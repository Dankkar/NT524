#!/usr/bin/env python3
"""Feedback API for WAF blocked-request review and ML/WAF rule tuning."""

from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import datetime as dt
import html
import importlib.util
import json
import os
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("FEEDBACK_PORT", "5005"))
ES_SEARCH_URL = os.environ.get(
    "FEEDBACK_ES_SEARCH_URL",
    "http://172.10.10.1:9200/siem-waf-access-*/_search",
)
DEFAULT_REVIEWER = os.environ.get("FEEDBACK_REVIEWER", "operator")

DATASET_DIRS = [
    PROJECT_ROOT / "data" / "dataset",
    PROJECT_ROOT / "modsec-learn" / "data" / "dataset",
]
AUDIT_LOG = PROJECT_ROOT / "data" / "feedback" / "feedback_audit.jsonl"
EXPORT_SCRIPT = PROJECT_ROOT / "scripts" / "export_tuned_rules.py"
MODSEC_LEARN_DIR = PROJECT_ROOT / "modsec-learn"
DEFAULT_ML_PYTHON = Path(os.environ.get("FEEDBACK_ML_PYTHON", "~/modsec-ai-venv/bin/python")).expanduser()


def now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def display_path(path):
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def html_response(handler, status, body):
    data = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def error_response(handler, status, message):
    json_response(handler, status, {"ok": False, "error": message})


def read_json_body(handler):
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8")
    content_type = handler.headers.get("Content-Type", "")
    if "application/json" in content_type:
        return json.loads(raw or "{}")
    return {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}


def load_json_list(path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(item) for item in data]
    except Exception:
        return []
    return []


def atomic_write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=4)
            tmp.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def unique_sorted(items):
    return sorted(set(str(item) for item in items if str(item).strip()))


def dataset_paths(dataset_dir):
    return {
        "legitimate": dataset_dir / "legitimate_train.json",
        "malicious": dataset_dir / "malicious_train.json",
    }


def read_dataset(dataset_dir):
    paths = dataset_paths(dataset_dir)
    return {
        "legitimate": load_json_list(paths["legitimate"]),
        "malicious": load_json_list(paths["malicious"]),
    }


def get_known_labels():
    legitimate = set()
    malicious = set()
    for dataset_dir in DATASET_DIRS:
        data = read_dataset(dataset_dir)
        legitimate.update(data["legitimate"])
        malicious.update(data["malicious"])
    return legitimate, malicious


def label_payload(payload, label, reviewer=DEFAULT_REVIEWER, es_id=None, note=None):
    if not payload or not str(payload).strip():
        raise ValueError("payload is required")

    label = str(label).lower().strip()
    if label in ("0", "legit", "benign", "legitimate", "false_positive"):
        target = "legitimate"
        opposite = "malicious"
    elif label in ("1", "attack", "malicious", "true_positive"):
        target = "malicious"
        opposite = "legitimate"
    else:
        raise ValueError("label must be legitimate or malicious")

    payload = str(payload)
    changed = []
    summary = {}

    for dataset_dir in DATASET_DIRS:
        dataset_dir.mkdir(parents=True, exist_ok=True)
        data = read_dataset(dataset_dir)
        before = {k: len(v) for k, v in data.items()}

        target_values = set(data[target])
        opposite_values = set(data[opposite])
        target_values.add(payload)
        opposite_values.discard(payload)

        data[target] = unique_sorted(target_values)
        data[opposite] = unique_sorted(opposite_values)

        paths = dataset_paths(dataset_dir)
        atomic_write_json(paths["legitimate"], data["legitimate"])
        atomic_write_json(paths["malicious"], data["malicious"])

        after = {k: len(v) for k, v in data.items()}
        summary[display_path(dataset_dir)] = {"before": before, "after": after}
        changed.append(str(dataset_dir))

    audit_event = {
        "timestamp": now_iso(),
        "payload": payload,
        "label": target,
        "reviewer": reviewer or DEFAULT_REVIEWER,
        "es_id": es_id,
        "note": note,
        "dataset_dirs": changed,
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as audit:
        audit.write(json.dumps(audit_event, ensure_ascii=False) + "\n")

    return {
        "ok": True,
        "payload": payload,
        "label": target,
        "dataset_summary": summary,
        "audit_log": display_path(AUDIT_LOG),
    }


def extract_payload(uri):
    parsed_uri = urllib.parse.urlparse(uri or "")
    if parsed_uri.query:
        return urllib.parse.unquote_plus(parsed_uri.query)
    return ""


def normalize_hit(hit, idx):
    source = hit.get("_source", {})
    message_raw = source.get("message", "") or ""

    client_ip = source.get("client_ip")
    uri = source.get("request_path")
    status_code = source.get("status_code")
    method = source.get("http_method")
    timestamp = source.get("@timestamp") or source.get("time_local") or "Unknown"

    if client_ip is None or uri is None or status_code is None:
        try:
            message_json = json.loads(message_raw)
            log_line = message_json.get("log", "").strip()
        except Exception:
            log_line = message_raw.strip()

        match = re.match(r'^(\S+) - \S+ \[(.*?)\] "(\S+) (\S+) \S+" (\d+)', log_line)
        if match:
            client_ip = match.group(1)
            timestamp = timestamp if timestamp != "Unknown" else match.group(2)
            method = match.group(3)
            uri = match.group(4)
            status_code = int(match.group(5))
        else:
            client_ip = client_ip or "Unknown"
            uri = uri or log_line
            status_code = int(status_code or 0)

    try:
        status_code = int(status_code)
    except Exception:
        status_code = 0

    payload = extract_payload(uri)
    return {
        "id": f"log_{idx}",
        "es_id": hit.get("_id", "N/A"),
        "timestamp": timestamp,
        "client_ip": client_ip or "Unknown",
        "method": method or "GET",
        "uri": uri or "",
        "payload": payload,
        "status_code": status_code,
        "rule_id": source.get("modsec_rule_id"),
        "rule_message": source.get("modsec_msg"),
        "host": (source.get("host") or {}).get("name"),
    }


def fetch_recent_blocked_logs(limit=1000):
    query = {
        "size": int(limit),
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {
            "bool": {
                "should": [
                    {"term": {"status_code": 403}},
                    {"term": {"tags": "waf_blocked"}},
                ],
                "minimum_should_match": 1,
            }
        },
    }

    req = urllib.request.Request(
        ES_SEARCH_URL,
        data=json.dumps(query).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    logs = []
    seen_payloads = set()
    with urllib.request.urlopen(req, timeout=10) as res:
        response_data = json.loads(res.read().decode("utf-8"))
        hits = response_data.get("hits", {}).get("hits", [])

    legitimate, malicious = get_known_labels()
    for idx, hit in enumerate(hits):
        log = normalize_hit(hit, idx)
        payload = log["payload"]
        if log["status_code"] != 403 or not payload or payload in seen_payloads:
            continue
        seen_payloads.add(payload)
        if payload in malicious:
            log["current_label"] = "malicious"
        elif payload in legitimate:
            log["current_label"] = "legitimate"
        else:
            log["current_label"] = "unreviewed"
        logs.append(log)
    return logs


def dataset_status():
    status = {}
    legitimate_all, malicious_all = get_known_labels()
    for dataset_dir in DATASET_DIRS:
        data = read_dataset(dataset_dir)
        status[display_path(dataset_dir)] = {
            "exists": dataset_dir.exists(),
            "legitimate": len(data["legitimate"]),
            "malicious": len(data["malicious"]),
        }
    return {
        "ok": True,
        "dataset_dirs": status,
        "combined": {
            "legitimate": len(legitimate_all),
            "malicious": len(malicious_all),
            "overlap": len(legitimate_all.intersection(malicious_all)),
        },
        "audit_log": display_path(AUDIT_LOG),
    }


def export_rules(model="linear_svc_pl4_l1.joblib", threshold="1e-5"):
    if not MODSEC_LEARN_DIR.exists():
        raise RuntimeError("modsec-learn directory not found")
    python_bin = DEFAULT_ML_PYTHON if DEFAULT_ML_PYTHON.exists() else Path("python3")
    missing = []
    if python_bin.name == "python3":
        missing = [name for name in ("joblib", "sklearn", "toml") if importlib.util.find_spec(name) is None]
    if missing:
        return {
            "ok": False,
            "returncode": 127,
            "missing_dependencies": missing,
            "stderr": (
                "Missing Python dependencies for ML rule export. "
                "Activate ~/modsec-ai-venv or install modsec-learn requirements first: "
                "python3 -m pip install -r modsec-learn/requirements.txt"
            ),
            "rule_file": "ansible/roles/nginx_waf/files/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf",
        }
    cmd = [
        str(python_bin),
        os.path.relpath(EXPORT_SCRIPT, MODSEC_LEARN_DIR),
        "--model",
        model,
        "--threshold",
        str(threshold),
    ]
    result = subprocess.run(
        cmd,
        cwd=str(MODSEC_LEARN_DIR),
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout[-12000:],
        "stderr": result.stderr[-4000:],
        "rule_file": "ansible/roles/nginx_waf/files/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf",
    }


def render_dashboard():
    try:
        logs = fetch_recent_blocked_logs()
        es_error = ""
    except Exception as exc:
        logs = []
        es_error = str(exc)

    status = dataset_status()
    rows = []
    for log in logs:
        payload_json = html.escape(json.dumps(log["payload"]))
        label = log["current_label"]
        if label == "malicious":
            action_html = '<span class="badge badge-danger">Confirmed Attack</span>'
        elif label == "legitimate":
            action_html = '<span class="badge badge-ok">Reclassified Benign</span>'
        else:
            action_html = f"""
              <button class="btn btn-ok" onclick='submitFeedback({payload_json}, "legitimate", "{html.escape(log["es_id"])}")'>Legitimate</button>
              <button class="btn btn-danger" onclick='submitFeedback({payload_json}, "malicious", "{html.escape(log["es_id"])}")'>Attack</button>
            """

        rows.append(
            f"""
            <tr>
              <td>{html.escape(str(log["timestamp"]))}</td>
              <td>{html.escape(str(log["host"] or ""))}</td>
              <td class="mono">{html.escape(str(log["es_id"]))}</td>
              <td><span class="badge">{html.escape(str(log["client_ip"]))}</span></td>
              <td class="mono ellipsis">{html.escape(str(log["uri"]))}</td>
              <td class="payload">{html.escape(str(log["payload"]))}</td>
              <td>{action_html}</td>
            </tr>
            """
        )

    if not rows:
        message = "No WAF blocked requests with query payloads were found."
        if es_error:
            message = f"Elasticsearch query failed: {html.escape(es_error)}"
        rows.append(f'<tr><td colspan="7" class="empty">{message}</td></tr>')

    combined = status["combined"]
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>WAF Feedback API</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 28px; background: #0f172a; color: #e2e8f0; }}
    h1 {{ margin: 0 0 6px; font-size: 24px; }}
    .sub {{ color: #94a3b8; margin-bottom: 20px; }}
    .toolbar {{ display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }}
    .stat {{ background: #111827; border: 1px solid #334155; border-radius: 8px; padding: 10px 12px; }}
    table {{ width: 100%; border-collapse: collapse; background: #111827; border: 1px solid #334155; }}
    th, td {{ padding: 10px; border-bottom: 1px solid #243244; text-align: left; vertical-align: top; }}
    th {{ color: #93c5fd; font-size: 12px; text-transform: uppercase; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }}
    .ellipsis {{ max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .payload {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; max-width: 340px; word-break: break-word; color: #f8fafc; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 3px 8px; background: #1e293b; color: #bfdbfe; font-size: 12px; }}
    .badge-ok {{ background: #064e3b; color: #86efac; }}
    .badge-danger {{ background: #7f1d1d; color: #fecaca; }}
    .btn {{ border: 1px solid #475569; border-radius: 6px; padding: 7px 10px; cursor: pointer; color: #e2e8f0; background: #1e293b; }}
    .btn-ok {{ border-color: #16a34a; color: #86efac; }}
    .btn-danger {{ border-color: #dc2626; color: #fecaca; }}
    .empty {{ text-align: center; color: #94a3b8; padding: 28px; }}
    #notice {{ position: fixed; right: 20px; bottom: 20px; display: none; background: #1e293b; border-left: 4px solid #38bdf8; padding: 12px 16px; border-radius: 6px; }}
  </style>
  <script>
    function notice(message) {{
      const el = document.getElementById("notice");
      el.textContent = message;
      el.style.display = "block";
      setTimeout(() => el.style.display = "none", 3500);
    }}
    async function submitFeedback(payload, label, esId) {{
      const res = await fetch("/api/feedback", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{payload: payload, label: label, es_id: esId}})
      }});
      const data = await res.json();
      if (!res.ok || !data.ok) {{
        notice(data.error || "Feedback failed");
        return;
      }}
      notice("Saved " + label + " label. Dataset updated.");
      setTimeout(() => window.location.reload(), 700);
    }}
    async function exportRules() {{
      notice("Exporting tuned rules...");
      const res = await fetch("/api/export-rules", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{model: "linear_svc_pl4_l1.joblib", threshold: "1e-5"}})
      }});
      const data = await res.json();
      notice(data.ok ? "Rule export complete." : "Rule export failed.");
    }}
  </script>
</head>
<body>
  <h1>WAF Feedback API</h1>
  <div class="sub">Review WAF blocked payloads, label false positives/attacks, and feed the ML/WAF tuning loop.</div>
  <div class="toolbar">
    <div class="stat">Combined legitimate: <b>{combined["legitimate"]}</b></div>
    <div class="stat">Combined malicious: <b>{combined["malicious"]}</b></div>
    <div class="stat">Overlap conflicts: <b>{combined["overlap"]}</b></div>
    <button class="btn" onclick="window.location.reload()">Refresh</button>
    <button class="btn" onclick="exportRules()">Export Tuned Rules</button>
    <a class="btn" href="/api/dataset/status" style="text-decoration:none;">Dataset Status JSON</a>
  </div>
  <table>
    <thead>
      <tr>
        <th>Timestamp</th><th>Host</th><th>ES ID</th><th>Client</th><th>URI</th><th>Payload</th><th>Feedback</th>
      </tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
  </table>
  <div id="notice"></div>
</body>
</html>
"""


class FeedbackHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{now_iso()}] {self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/":
            html_response(self, 200, render_dashboard())
            return
        if parsed.path == "/healthz":
            json_response(self, 200, {"ok": True, "status": "ok"})
            return
        if parsed.path == "/api/blocked":
            limit = int(params.get("limit", ["1000"])[0])
            try:
                json_response(self, 200, {"ok": True, "logs": fetch_recent_blocked_logs(limit)})
            except Exception as exc:
                error_response(self, 502, f"failed to query Elasticsearch: {exc}")
            return
        if parsed.path == "/api/dataset/status":
            json_response(self, 200, dataset_status())
            return
        if parsed.path == "/feedback":
            # Backward-compatible GET endpoint used by the original dashboard.
            payload = params.get("payload", [""])[0]
            label = params.get("label", [""])[0]
            try:
                result = label_payload(payload, label, es_id=params.get("es_id", [None])[0])
                json_response(self, 200, result)
            except ValueError as exc:
                error_response(self, 400, str(exc))
            except Exception as exc:
                error_response(self, 500, str(exc))
            return

        error_response(self, 404, "not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            body = read_json_body(self)
        except Exception as exc:
            error_response(self, 400, f"invalid request body: {exc}")
            return

        if parsed.path == "/api/feedback":
            try:
                result = label_payload(
                    payload=body.get("payload"),
                    label=body.get("label"),
                    reviewer=body.get("reviewer") or DEFAULT_REVIEWER,
                    es_id=body.get("es_id"),
                    note=body.get("note"),
                )
                json_response(self, 200, result)
            except ValueError as exc:
                error_response(self, 400, str(exc))
            except Exception as exc:
                error_response(self, 500, str(exc))
            return

        if parsed.path == "/api/export-rules":
            try:
                result = export_rules(
                    model=body.get("model", "linear_svc_pl4_l1.joblib"),
                    threshold=body.get("threshold", "1e-5"),
                )
                json_response(self, 200 if result["ok"] else 500, result)
            except Exception as exc:
                error_response(self, 500, str(exc))
            return

        error_response(self, 404, "not found")


def run():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, FeedbackHandler)
    print(f"[INFO] WAF Feedback API listening on 0.0.0.0:{PORT}")
    print(f"[INFO] Elasticsearch search URL: {ES_SEARCH_URL}")
    print("[INFO] Dataset dirs:")
    for dataset_dir in DATASET_DIRS:
        print(f"  - {dataset_dir}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    print("[INFO] Feedback API stopped.")


if __name__ == "__main__":
    run()
