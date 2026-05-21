from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import urllib.request
import json
import os
import re

PORT = 5005
DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/dataset"))
ES_URL = "http://172.10.10.1:9200/siem-hybrid-*/_search"

def fetch_recent_blocked_logs():
    # Query Elasticsearch for the last 1000 WAF logs
    query = {
        "size": 1000,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {
            "bool": {
                "must": [
                    {"term": {"fields.node_role.keyword": "waf"}}
                ]
            }
        }
    }
    
    req = urllib.request.Request(
        ES_URL,
        data=json.dumps(query).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    logs = []
    seen_payloads = set()
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            response_data = json.loads(res.read().decode("utf-8"))
            hits = response_data.get("hits", {}).get("hits", [])
            for idx, hit in enumerate(hits):
                source = hit.get("_source", {})
                message_raw = source.get("message", "")
                
                # Parse Nginx log line from JSON nested format
                try:
                    message_json = json.loads(message_raw)
                    log_line = message_json.get("log", "").strip()
                except Exception:
                    log_line = message_raw.strip()
                
                # Nginx access log parsing regex
                pattern = r'^(\S+) - \S+ \[(.*?)\] "(\S+) (\S+) \S+" (\d+)'
                match = re.match(pattern, log_line)
                if match:
                    client_ip = match.group(1)
                    timestamp = match.group(2)
                    uri = match.group(4)
                    status_code = int(match.group(5))
                else:
                    client_ip = "Unknown"
                    timestamp = source.get("@timestamp", "Unknown")
                    uri = log_line
                    status_code = 0
                
                # Extract query payload
                parsed_uri = urllib.parse.urlparse(uri)
                payload = urllib.parse.unquote(parsed_uri.query) if parsed_uri.query else ""
                
                # Only display logs that have query payloads and status 403 (blocked)
                if status_code == 403 and payload:
                    if payload not in seen_payloads:
                        seen_payloads.add(payload)
                        logs.append({
                            "id": f"log_{idx}",
                            "es_id": hit.get("_id", "N/A"),
                            "timestamp": timestamp,
                            "client_ip": client_ip,
                            "uri": uri,
                            "payload": payload
                        })
    except Exception as e:
        print(f"[ERROR] Failed to fetch logs from ES: {e}")
        
    return logs


class FeedbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        if parsed_url.path == "/":
            # Serve the interactive SOC Dashboard
            logs = fetch_recent_blocked_logs()
            
            legitimate_path = os.path.join(DATASET_DIR, "legitimate_train.json")
            malicious_path = os.path.join(DATASET_DIR, "malicious_train.json")
            
            legitimate_payloads = set()
            malicious_payloads = set()
            
            if os.path.exists(legitimate_path):
                try:
                    with open(legitimate_path, "r") as f:
                        legitimate_payloads = set(json.load(f))
                except Exception:
                    pass
            if os.path.exists(malicious_path):
                try:
                    with open(malicious_path, "r") as f:
                        malicious_payloads = set(json.load(f))
                except Exception:
                    pass
            
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            
            # Construct table rows
            table_rows = ""
            if not logs:
                table_rows = """
                <tr>
                    <td colspan="6" style="text-align: center; color: #64748b; padding: 30px;">
                        No WAF blocked requests found with query payloads in Elasticsearch.
                    </td>
                </tr>
                """
            for log in logs:
                # Check if already classified
                if log['payload'] in malicious_payloads:
                    action_html = '<span class="badge" style="background: rgba(239, 68, 68, 0.2); color: #f87171;">Confirmed Attack</span>'
                elif log['payload'] in legitimate_payloads:
                    action_html = '<span class="badge" style="background: rgba(34, 197, 94, 0.2); color: #4ade80;">Reclassified Benign</span>'
                else:
                    action_html = f"""
                        <button class="btn btn-benign" onclick="submitFeedback('{log['id']}', 0, '{urllib.parse.quote(log['payload'])}')">Legitimate (False Positive) 🟢</button>
                        <button class="btn btn-malicious" onclick="submitFeedback('{log['id']}', 1, '{urllib.parse.quote(log['payload'])}')">Confirm Attack 🔴</button>
                    """
                
                table_rows += f"""
                <tr id="{log['id']}">
                    <td>{log['timestamp']}</td>
                    <td style="font-family: monospace; font-size: 11px; color: #64748b;">{log['es_id']}</td>
                    <td><span class="badge ip-badge">{log['client_ip']}</span></td>
                    <td style="font-family: monospace; font-size: 13px; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{log['uri']}</td>
                    <td class="payload-text">{log['payload']}</td>
                    <td>{action_html}</td>
                </tr>
                """

                
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>SOC WAF Incident Management Dashboard</title>
                <style>
                    body {{
                        font-family: 'Outfit', sans-serif;
                        background: #0b0f19;
                        color: #f1f5f9;
                        margin: 0;
                        padding: 40px;
                        display: flex;
                        justify-content: center;
                    }}
                    .container {{
                        width: 100%;
                        max-width: 1200px;
                    }}
                    .header {{
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 30px;
                    }}
                    h1 {{
                        margin: 0;
                        color: #38bdf8;
                        font-size: 28px;
                        font-weight: 700;
                        letter-spacing: -0.5px;
                    }}
                    .subtitle {{
                        color: #64748b;
                        margin-top: 5px;
                    }}
                    .card {{
                        background: rgba(17, 24, 39, 0.7);
                        backdrop-filter: blur(20px);
                        border: 1px solid rgba(255, 255, 255, 0.05);
                        border-radius: 16px;
                        padding: 24px;
                        box-shadow: 0 20px 40px rgba(0,0,0,0.5);
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        text-align: left;
                    }}
                    th {{
                        padding: 16px;
                        color: #94a3b8;
                        border-bottom: 2px solid rgba(255,255,255,0.05);
                        font-weight: 600;
                    }}
                    td {{
                        padding: 16px;
                        border-bottom: 1px solid rgba(255,255,255,0.05);
                        color: #cbd5e1;
                    }}
                    tr:hover {{
                        background: rgba(255,255,255,0.02);
                    }}
                    .badge {{
                        padding: 4px 10px;
                        border-radius: 9999px;
                        font-size: 12px;
                        font-weight: bold;
                    }}
                    .ip-badge {{
                        background: #1e293b;
                        color: #38bdf8;
                    }}
                    .payload-text {{
                        font-family: 'Fira Code', monospace;
                        background: #020617;
                        padding: 6px 10px;
                        border-radius: 6px;
                        font-size: 13px;
                        color: #e2e8f0;
                        border-left: 3px solid #64748b;
                        max-width: 300px;
                        word-break: break-all;
                    }}
                    .btn {{
                        padding: 8px 14px;
                        border: none;
                        border-radius: 8px;
                        cursor: pointer;
                        font-size: 12px;
                        font-weight: 600;
                        transition: all 0.2s ease;
                        margin-right: 6px;
                    }}
                    .btn-benign {{
                        background: rgba(34, 197, 94, 0.15);
                        color: #4ade80;
                        border: 1px solid rgba(34, 197, 94, 0.3);
                    }}
                    .btn-benign:hover {{
                        background: #22c55e;
                        color: #ffffff;
                    }}
                    .btn-malicious {{
                        background: rgba(239, 68, 68, 0.15);
                        color: #f87171;
                        border: 1px solid rgba(239, 68, 68, 0.3);
                    }}
                    .btn-malicious:hover {{
                        background: #ef4444;
                        color: #ffffff;
                    }}
                    .status-cell {{
                        font-weight: bold;
                        text-transform: uppercase;
                        font-size: 11px;
                        letter-spacing: 1px;
                    }}
                    .alert-success {{
                        color: #4ade80;
                    }}
                    .alert-danger {{
                        color: #f87171;
                    }}
                    .notification {{
                        position: fixed;
                        bottom: 20px;
                        right: 20px;
                        padding: 15px 25px;
                        background: #1e293b;
                        border-left: 4px solid #38bdf8;
                        border-radius: 8px;
                        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                        display: none;
                        z-index: 1000;
                        font-size: 14px;
                    }}
                </style>
                <script>
                    function showNotification(message) {{
                        const el = document.getElementById('notification');
                        el.innerText = message;
                        el.style.display = 'block';
                        setTimeout(() => {{
                            el.style.display = 'none';
                        }}, 4000);
                    }}
                    
                    function submitFeedback(rowId, label, encodedPayload) {{
                        const payload = decodeURIComponent(encodedPayload);
                        const url = `/feedback?label=${{label}}&payload=${{encodedPayload}}`;
                        
                        fetch(url)
                            .then(response => {{
                                if (response.ok) {{
                                    const row = document.getElementById(rowId);
                                    const actionCell = row.cells[5];
                                    if (label === 0) {{
                                        actionCell.innerHTML = '<span class="badge" style="background: rgba(34, 197, 94, 0.2); color: #4ade80;">Reclassified Benign</span>';
                                        showNotification('Payload re-classified as benign (legitimate).');
                                    }} else {{
                                        actionCell.innerHTML = '<span class="badge" style="background: rgba(239, 68, 68, 0.2); color: #f87171;">Confirmed Attack</span>';
                                        showNotification('Payload confirmed as malicious attack.');
                                    }}
                                }} else {{
                                    showNotification('Failed to register feedback.');
                                }}
                            }})
                            .catch(err => {{
                                showNotification('Connection error.');
                            }});
                    }}
                </script>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div>
                            <h1>WAF SOC Incident Management</h1>
                            <div class="subtitle">Review blocked requests and feedback labels to retrain the ML model</div>
                        </div>
                        <button class="btn" style="background: #1e293b; color: #f1f5f9; border: 1px solid rgba(255,255,255,0.1);" onclick="window.location.reload()">Refresh Logs 🔄</button>
                    </div>
                    <div class="card">
                        <table>
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>ES Doc ID</th>
                                    <th>Client IP</th>
                                    <th>Request URI</th>
                                    <th>Extracted Payload</th>
                                    <th>Actions / Feedback</th>
                                </tr>
                            </thead>
                            <tbody>
                                {table_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div id="notification" class="notification"></div>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
            
        elif parsed_url.path == "/feedback":
            params = urllib.parse.parse_qs(parsed_url.query)
            label_list = params.get("label")
            payload_list = params.get("payload")
            
            if not label_list or not payload_list:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<h1>Error: Missing label or payload</h1>".encode("utf-8"))
                return
                
            label = int(label_list[0])
            payload = payload_list[0]
            
            legitimate_path = os.path.join(DATASET_DIR, "legitimate_train.json")
            malicious_path = os.path.join(DATASET_DIR, "malicious_train.json")
            
            # Load files
            legitimate_payloads = []
            malicious_payloads = []
            
            if os.path.exists(legitimate_path):
                try:
                    with open(legitimate_path, "r") as f:
                        legitimate_payloads = json.load(f)
                except Exception:
                    pass
            if os.path.exists(malicious_path):
                try:
                    with open(malicious_path, "r") as f:
                        malicious_payloads = json.load(f)
                except Exception:
                    pass
                    
            if label == 0:
                # False Positive -> Add to Legitimate, remove from Malicious
                if payload not in legitimate_payloads:
                    legitimate_payloads.append(payload)
                if payload in malicious_payloads:
                    malicious_payloads.remove(payload)
                status_msg = "Successfully reported False Positive. Payload re-classified as Legitimate (benign)."
            else:
                # True Positive -> Add to Malicious, remove from Legitimate
                if payload not in malicious_payloads:
                    malicious_payloads.append(payload)
                if payload in legitimate_payloads:
                    legitimate_payloads.remove(payload)
                status_msg = "Successfully confirmed True Positive. Payload re-classified as Malicious (attack)."
                
            # Save files
            with open(legitimate_path, "w") as f:
                json.dump(legitimate_payloads, f, indent=4)
            with open(malicious_path, "w") as f:
                json.dump(malicious_payloads, f, indent=4)
                
            # Send HTML response
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>SOC WAF Feedback System</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: #0f172a;
                        color: #f8fafc;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }}
                    .card {{
                        background: rgba(30, 41, 59, 0.7);
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        padding: 30px;
                        border-radius: 12px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                        max-width: 500px;
                        text-align: center;
                    }}
                    h2 {{
                        color: #38bdf8;
                        margin-top: 0;
                    }}
                    .payload {{
                        background: #020617;
                        padding: 10px;
                        border-radius: 6px;
                        font-family: monospace;
                        font-size: 14px;
                        word-break: break-all;
                        margin: 15px 0;
                        border-left: 4px solid #38bdf8;
                    }}
                    .success-badge {{
                        background: #22c55e;
                        color: #ffffff;
                        display: inline-block;
                        padding: 5px 12px;
                        border-radius: 9999px;
                        font-size: 12px;
                        font-weight: bold;
                        margin-bottom: 15px;
                    }}
                    .footer {{
                        color: #64748b;
                        font-size: 12px;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="card">
                    <span class="success-badge">SUCCESS</span>
                    <h2>SOC Feedback Registered</h2>
                    <p>{status_msg}</p>
                    <div class="payload">{payload}</div>
                    <p>The local training dataset has been updated. You can run the retraining script to update WAF weights.</p>
                    <div class="footer">WAF MLOps SIEM Feedback Loop API</div>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=FeedbackHandler):
    server_address = ('', PORT)
    httpd = server_class(server_address, handler_class)
    print(f"[INFO] SOC WAF Feedback server running on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    print("[INFO] Server stopped.")

if __name__ == "__main__":
    run()
