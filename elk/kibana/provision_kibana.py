#!/usr/bin/env python3
"""Provision Kibana: data views, WAF security dashboard, service health dashboard, alert rules."""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

KIBANA_URL = "http://127.0.0.1:5601"
# Index patterns
IDX_WAF    = "siem-waf-access-*"
IDX_APP    = "siem-app-access-*"
IDX_GATEWAY = "siem-gateway-access-*"
IDX_SYSLOG = "siem-syslog-*"
IDX_ALL    = "siem-*"


def request(method, path, body=None, expected=(200, 201)):
    data = None
    headers = {"kbn-xsrf": "true"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{KIBANA_URL}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read().decode("utf-8")
            if resp.status not in expected:
                raise RuntimeError(f"{method} {path} → {resp.status}: {payload}")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        if exc.code not in expected:
            raise RuntimeError(f"{method} {path} → {exc.code}: {payload}") from exc
        return json.loads(payload) if payload else {}


def put_saved_object(obj_type, obj_id, attributes, references=None):
    return request(
        "POST",
        f"/api/saved_objects/{obj_type}/{obj_id}?overwrite=true",
        {"attributes": attributes, "references": references or []},
    )


# ─── Data Views ───────────────────────────────────────────────────────────────

def create_data_views():
    views = [
        ("siem-all-data-view",    IDX_ALL,    "SIEM – All Logs"),
        ("siem-waf-data-view",    IDX_WAF,    "SIEM – WAF Access"),
        ("siem-app-data-view",    IDX_APP,    "SIEM – App Access"),
        ("siem-gateway-data-view", IDX_GATEWAY, "SIEM – Gateway Access"),
        ("siem-syslog-data-view", IDX_SYSLOG, "SIEM – Syslog"),
    ]
    for dv_id, pattern, name in views:
        request(
            "POST",
            "/api/data_views/data_view",
            {
                "data_view": {
                    "id": dv_id,
                    "title": pattern,
                    "name": name,
                    "timeFieldName": "@timestamp",
                },
                "override": True,
            },
            expected=(200, 201),
        )
        print(f"  data view: {name}")


# ─── Vega helpers ─────────────────────────────────────────────────────────────

def vega_vis(title, spec):
    return {
        "title": title,
        "visState": json.dumps(
            {"title": title, "type": "vega", "params": {"spec": json.dumps(spec)}, "aggs": []}
        ),
        "uiStateJSON": "{}",
        "description": "",
        "version": 1,
        "kibanaSavedObjectMeta": {"searchSourceJSON": "{}"},
    }


def time_range_query(gte="now-24h"):
    return {"range": {"@timestamp": {"gte": gte, "lte": "now"}}}


def bar_over_time(index, title, extra_query=None):
    query = time_range_query()
    if extra_query:
        query = {"bool": {"must": [query, extra_query]}}
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": title,
        "data": {
            "url": {
                "index": index,
                "body": {
                    "size": 0,
                    "query": query,
                    "aggs": {
                        "events": {
                            "date_histogram": {
                                "field": "@timestamp",
                                "fixed_interval": "5m",
                                "min_doc_count": 0,
                            }
                        }
                    },
                },
            },
            "format": {"property": "aggregations.events.buckets"},
        },
        "mark": {"type": "bar", "tooltip": True},
        "encoding": {
            "x": {"field": "key", "type": "temporal", "title": "Time"},
            "y": {"field": "doc_count", "type": "quantitative", "title": "Count"},
        },
    }


def top_terms_bar(index, field, title, size=15, extra_query=None):
    query = time_range_query()
    if extra_query:
        query = {"bool": {"must": [query, extra_query]}}
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": title,
        "data": {
            "url": {
                "index": index,
                "body": {
                    "size": 0,
                    "query": query,
                    "aggs": {"terms": {"terms": {"field": field, "size": size}}},
                },
            },
            "format": {"property": "aggregations.terms.buckets"},
        },
        "mark": {"type": "bar", "tooltip": True},
        "encoding": {
            "y": {"field": "key", "type": "nominal", "title": field.split(".")[0], "sort": "-x"},
            "x": {"field": "doc_count", "type": "quantitative", "title": "Count"},
            "color": {"field": "key", "type": "nominal", "legend": None},
        },
    }


def status_breakdown(index, title):
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": title,
        "data": {
            "url": {
                "index": index,
                "body": {
                    "size": 0,
                    "query": time_range_query(),
                    "aggs": {
                        "status": {
                            "terms": {"field": "status_code", "size": 20}
                        }
                    },
                },
            },
            "format": {"property": "aggregations.status.buckets"},
        },
        "mark": {"type": "arc", "tooltip": True},
        "encoding": {
            "theta": {"field": "doc_count", "type": "quantitative"},
            "color": {"field": "key", "type": "nominal", "title": "HTTP Status"},
        },
    }


def log_volume_by_node(title):
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": title,
        "data": {
            "url": {
                "index": IDX_ALL,
                "body": {
                    "size": 0,
                    "query": time_range_query(),
                    "aggs": {
                        "nodes": {
                            "terms": {"field": "host.name.keyword", "size": 10}
                        }
                    },
                },
            },
            "format": {"property": "aggregations.nodes.buckets"},
        },
        "mark": {"type": "bar", "tooltip": True},
        "encoding": {
            "y": {"field": "key", "type": "nominal", "title": "Host", "sort": "-x"},
            "x": {"field": "doc_count", "type": "quantitative", "title": "Log Volume"},
            "color": {"field": "key", "type": "nominal", "legend": None},
        },
    }


# ─── WAF Security Dashboard ───────────────────────────────────────────────────

def create_waf_dashboard():
    q_blocked = {"term": {"status_code": 403}}

    vis_objects = {
        "waf-403-over-time": (
            "WAF – 403 Blocked Events over Time",
            bar_over_time(IDX_WAF, "Blocked Requests over Time (5 min)", q_blocked),
        ),
        "waf-top-blocked-ips": (
            "WAF – Top Blocked Client IPs",
            top_terms_bar(IDX_WAF, "client_ip.keyword", "Top IPs Blocked by WAF", extra_query=q_blocked),
        ),
        "waf-top-blocked-paths": (
            "WAF – Top Blocked Paths",
            top_terms_bar(IDX_WAF, "request_path.keyword", "Top Paths Blocked by WAF", extra_query=q_blocked),
        ),
        "waf-status-breakdown": (
            "WAF – HTTP Status Code Breakdown",
            status_breakdown(IDX_WAF, "HTTP Status Code Distribution (WAF)"),
        ),
        "waf-request-rate": (
            "WAF – Total Request Rate",
            bar_over_time(IDX_WAF, "Total Requests over Time (5 min)"),
        ),
    }

    for vis_id, (title, spec) in vis_objects.items():
        put_saved_object("visualization", vis_id, vega_vis(title, spec))

    # Saved search for blocked request detail table (for false positive review)
    search_attrs = {
        "title": "WAF – Blocked Request Details (403)",
        "description": "All WAF-blocked requests – use to review false positives and update retrain data",
        "hits": 0,
        "columns": [
            "@timestamp", "client_ip", "http_method", "request_path",
            "status_code", "user_agent", "x_forwarded_for",
            "modsec_rule_id", "modsec_msg",
        ],
        "sort": [["@timestamp", "desc"]],
        "version": 1,
        "kibanaSavedObjectMeta": {
            "searchSourceJSON": json.dumps({
                "index": "siem-waf-data-view",
                "filter": [
                    {
                        "meta": {"index": "siem-waf-data-view", "negate": False, "disabled": False,
                                 "alias": None, "type": "phrase", "key": "status_code"},
                        "query": {"match_phrase": {"status_code": 403}},
                        "$state": {"store": "appState"},
                    }
                ],
                "query": {"query": "", "language": "kuery"},
                "highlight": {"pre_tags": ["@kibana-highlighted-field@"],
                              "post_tags": ["@/kibana-highlighted-field@"],
                              "fields": {"*": {}},
                              "fragment_size": 2147483647},
            })
        },
    }
    put_saved_object("search", "waf-blocked-detail-search", search_attrs,
                     references=[{"name": "kibanaSavedObjectMeta.searchSourceJSON.index",
                                  "type": "index-pattern", "id": "siem-waf-data-view"}])

    panel_ids = [
        ("waf-403-over-time",        0,  0, 48, 12),
        ("waf-status-breakdown",     0, 12, 24, 12),
        ("waf-request-rate",        24, 12, 24, 12),
        ("waf-top-blocked-ips",      0, 24, 24, 14),
        ("waf-top-blocked-paths",   24, 24, 24, 14),
    ]

    panels = []
    references = []
    for idx, (vis_id, x, y, w, h) in enumerate(panel_ids, 1):
        i = str(idx)
        panels.append({
            "version": "8.13.0",
            "gridData": {"x": x, "y": y, "w": w, "h": h, "i": i},
            "panelIndex": i,
            "embeddableConfig": {},
            "panelRefName": f"panel_{i}",
        })
        references.append({"name": f"panel_{i}", "type": "visualization", "id": vis_id})

    # Blocked detail search panel
    panels.append({
        "version": "8.13.0",
        "gridData": {"x": 0, "y": 38, "w": 48, "h": 16, "i": "6"},
        "panelIndex": "6",
        "embeddableConfig": {"columns": ["@timestamp", "client_ip", "http_method",
                                         "request_path", "status_code", "user_agent",
                                         "modsec_rule_id", "modsec_msg"]},
        "panelRefName": "panel_6",
    })
    references.append({"name": "panel_6", "type": "search", "id": "waf-blocked-detail-search"})

    put_saved_object(
        "dashboard", "siem-waf-security",
        {
            "title": "WAF Security – Attack & False Positive Review",
            "description": (
                "Monitor WAF-blocked requests (403/SQLi). "
                "Bottom table shows full request detail for false-positive review and retrain data collection."
            ),
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({"useMargins": True, "hidePanelTitles": False}),
            "timeRestore": False,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({"query": {"query": "", "language": "kuery"}, "filter": []})
            },
        },
        references,
    )
    print("  dashboard: WAF Security – Attack & False Positive Review")


# ─── Service Health Dashboard ─────────────────────────────────────────────────

def create_health_dashboard():
    q_5xx = {"range": {"status_code": {"gte": 500}}}

    vis_objects = {
        "health-log-volume": (
            "Health – Log Volume by Node",
            log_volume_by_node("Log Volume by Node (last 24h)"),
        ),
        "health-5xx-rate": (
            "Health – 5xx Error Rate (WAF)",
            bar_over_time(IDX_WAF, "5xx Error Rate over Time", q_5xx),
        ),
        "health-syslog-severity": (
            "Health – Syslog High-Severity Events",
            bar_over_time(IDX_SYSLOG, "Syslog High-Severity Events over Time",
                          {"term": {"tags": "syslog_high_severity"}}),
        ),
        "health-throughput": (
            "Health – Request Throughput (WAF)",
            bar_over_time(IDX_WAF, "Request Throughput over Time (5 min)"),
        ),
    }

    for vis_id, (title, spec) in vis_objects.items():
        put_saved_object("visualization", vis_id, vega_vis(title, spec))

    panel_ids = [
        ("health-throughput",       0,  0, 48, 12),
        ("health-log-volume",       0, 12, 24, 14),
        ("health-5xx-rate",        24, 12, 24, 14),
        ("health-syslog-severity",  0, 26, 48, 12),
    ]

    panels = []
    references = []
    for idx, (vis_id, x, y, w, h) in enumerate(panel_ids, 1):
        i = str(idx)
        panels.append({
            "version": "8.13.0",
            "gridData": {"x": x, "y": y, "w": w, "h": h, "i": i},
            "panelIndex": i,
            "embeddableConfig": {},
            "panelRefName": f"panel_{i}",
        })
        references.append({"name": f"panel_{i}", "type": "visualization", "id": vis_id})

    put_saved_object(
        "dashboard", "siem-service-health",
        {
            "title": "Service Health – Load & Error Monitoring",
            "description": "Monitor request throughput, 5xx errors, log volume per node, and high-severity syslog events.",
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({"useMargins": True, "hidePanelTitles": False}),
            "timeRestore": False,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({"query": {"query": "", "language": "kuery"}, "filter": []})
            },
        },
        references,
    )
    print("  dashboard: Service Health – Load & Error Monitoring")


# ─── Response dashboard ───────────────────────────────────────────────────────

def response_query():
    return {
        "bool": {
            "should": [
                {"term": {"status_code": 403}},
                {"range": {"status_code": {"gte": 500}}},
                {"term": {"tags": "waf_blocked"}},
                {"term": {"tags": "auth_denied"}},
                {"term": {"tags": "server_error"}},
                {"term": {"tags": "syslog_high_severity"}},
                {"match_phrase": {"message": "wg0"}},
                {"match_phrase": {"message": "wireguard"}},
                {"match_phrase": {"message": "oauth2-proxy"}},
            ],
            "minimum_should_match": 1,
        }
    }


def create_response_dashboard():
    q_response = response_query()
    q_auth = {
        "bool": {
            "should": [
                {"term": {"tags": "auth_flow"}},
                {"term": {"tags": "auth_denied"}},
                {"prefix": {"request_path.keyword": "/oauth2/"}},
            ],
            "minimum_should_match": 1,
        }
    }
    q_vpn_or_infra = {
        "bool": {
            "should": [
                {"term": {"tags": "syslog_high_severity"}},
                {"match_phrase": {"message": "wg0"}},
                {"match_phrase": {"message": "wireguard"}},
                {"match_phrase": {"message": "nginx"}},
                {"match_phrase": {"message": "filebeat"}},
                {"match_phrase": {"message": "logstash"}},
            ],
            "minimum_should_match": 1,
        }
    }

    vis_objects = {
        "response-events-over-time": (
            "Response – Events Requiring Action",
            bar_over_time(IDX_ALL, "Response Events over Time", q_response),
        ),
        "response-top-hosts": (
            "Response – Top Hosts",
            top_terms_bar(IDX_ALL, "host.name.keyword", "Top Hosts with Response Events", extra_query=q_response),
        ),
        "response-auth-events": (
            "Response – Auth/Gateway Events",
            bar_over_time(IDX_GATEWAY, "Auth and Gateway Events", q_auth),
        ),
        "response-infra-events": (
            "Response – VPN/SIEM/System Events",
            bar_over_time(IDX_SYSLOG, "VPN, SIEM and High-Severity System Events", q_vpn_or_infra),
        ),
        "response-waf-rules": (
            "Response – Top WAF Rule IDs",
            top_terms_bar(IDX_WAF, "modsec_rule_id.keyword", "Top WAF Rules for Review", extra_query={"term": {"tags": "waf_blocked"}}),
        ),
    }

    for vis_id, (title, spec) in vis_objects.items():
        put_saved_object("visualization", vis_id, vega_vis(title, spec))

    search_attrs = {
        "title": "Response – Review Queue",
        "description": "Events that should trigger an operator response: WAF blocks, 5xx, auth denial, VPN/SIEM/system errors.",
        "hits": 0,
        "columns": [
            "@timestamp", "host.name", "fields.node_role", "status_code",
            "client_ip", "http_method", "request_path", "tags", "message",
        ],
        "sort": [["@timestamp", "desc"]],
        "version": 1,
        "kibanaSavedObjectMeta": {
            "searchSourceJSON": json.dumps({
                "index": "siem-all-data-view",
                "filter": [],
                "query": {
                    "query": "status_code:403 or status_code >= 500 or tags:(waf_blocked or auth_denied or server_error or syslog_high_severity) or message:(wg0 or wireguard or oauth2-proxy)",
                    "language": "kuery",
                },
            })
        },
    }
    put_saved_object("search", "response-review-queue-search", search_attrs,
                     references=[{"name": "kibanaSavedObjectMeta.searchSourceJSON.index",
                                  "type": "index-pattern", "id": "siem-all-data-view"}])

    panel_ids = [
        ("response-events-over-time", 0, 0, 48, 12),
        ("response-auth-events", 0, 12, 24, 12),
        ("response-infra-events", 24, 12, 24, 12),
        ("response-top-hosts", 0, 24, 24, 14),
        ("response-waf-rules", 24, 24, 24, 14),
    ]

    panels = []
    references = []
    for idx, (vis_id, x, y, w, h) in enumerate(panel_ids, 1):
        i = str(idx)
        panels.append({
            "version": "8.13.0",
            "gridData": {"x": x, "y": y, "w": w, "h": h, "i": i},
            "panelIndex": i,
            "embeddableConfig": {},
            "panelRefName": f"panel_{i}",
        })
        references.append({"name": f"panel_{i}", "type": "visualization", "id": vis_id})

    panels.append({
        "version": "8.13.0",
        "gridData": {"x": 0, "y": 38, "w": 48, "h": 16, "i": "6"},
        "panelIndex": "6",
        "embeddableConfig": {"columns": ["@timestamp", "host.name", "fields.node_role",
                                         "status_code", "client_ip", "request_path",
                                         "tags", "message"]},
        "panelRefName": "panel_6",
    })
    references.append({"name": "panel_6", "type": "search", "id": "response-review-queue-search"})

    put_saved_object(
        "dashboard", "siem-response-operations",
        {
            "title": "Response Operations – WAF/Auth/Infra",
            "description": (
                "Operational response queue for WAF blocks, auth/gateway problems, 5xx errors, "
                "VPN events, and SIEM pipeline health issues."
            ),
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({"useMargins": True, "hidePanelTitles": False}),
            "timeRestore": False,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({"query": {"query": "", "language": "kuery"}, "filter": []})
            },
        },
        references,
    )
    print("  dashboard: Response Operations – WAF/Auth/Infra")


# ─── Legacy overview dashboard (keep) ────────────────────────────────────────

def create_overview_dashboard():
    base_q = {"range": {"@timestamp": {"gte": "now-24h", "lte": "now"}}}

    specs = {
        "siem-events-over-time": ("SIEM – Events over Time", {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "Events over time",
            "data": {"url": {"index": IDX_ALL, "body": {"size": 0, "query": base_q,
                "aggs": {"events": {"date_histogram": {"field": "@timestamp",
                    "fixed_interval": "5m", "min_doc_count": 0}}}}}},
            "format": {"property": "aggregations.events.buckets"},
            "mark": {"type": "bar", "tooltip": True},
            "encoding": {
                "x": {"field": "key", "type": "temporal", "title": "Time"},
                "y": {"field": "doc_count", "type": "quantitative", "title": "Events"},
            },
        }),
        "siem-events-by-role": ("SIEM – Events by Role", {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "Events by node role",
            "data": {"url": {"index": IDX_ALL, "body": {"size": 0, "query": base_q,
                "aggs": {"roles": {"terms": {"field": "fields.node_role.keyword", "size": 10}}}}}},
            "format": {"property": "aggregations.roles.buckets"},
            "mark": {"type": "bar", "tooltip": True},
            "encoding": {
                "x": {"field": "key", "type": "nominal", "title": "Role"},
                "y": {"field": "doc_count", "type": "quantitative", "title": "Events"},
                "color": {"field": "key", "type": "nominal", "legend": None},
            },
        }),
        "siem-top-hosts": ("SIEM – Top Hosts", {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "Top hosts",
            "data": {"url": {"index": IDX_ALL, "body": {"size": 0, "query": base_q,
                "aggs": {"hosts": {"terms": {"field": "host.name.keyword", "size": 10}}}}}},
            "format": {"property": "aggregations.hosts.buckets"},
            "mark": {"type": "bar", "tooltip": True},
            "encoding": {
                "y": {"field": "key", "type": "nominal", "title": "Host", "sort": "-x"},
                "x": {"field": "doc_count", "type": "quantitative", "title": "Events"},
                "color": {"field": "key", "type": "nominal", "legend": None},
            },
        }),
    }

    for vis_id, (title, spec) in specs.items():
        put_saved_object("visualization", vis_id, vega_vis(title, spec))

    panels = [
        {"version": "8.13.0", "gridData": {"x": 0, "y": 0, "w": 48, "h": 15, "i": "1"},
         "panelIndex": "1", "embeddableConfig": {}, "panelRefName": "panel_1"},
        {"version": "8.13.0", "gridData": {"x": 0, "y": 15, "w": 24, "h": 15, "i": "2"},
         "panelIndex": "2", "embeddableConfig": {}, "panelRefName": "panel_2"},
        {"version": "8.13.0", "gridData": {"x": 24, "y": 15, "w": 24, "h": 15, "i": "3"},
         "panelIndex": "3", "embeddableConfig": {}, "panelRefName": "panel_3"},
    ]
    references = [
        {"name": "panel_1", "type": "visualization", "id": "siem-events-over-time"},
        {"name": "panel_2", "type": "visualization", "id": "siem-events-by-role"},
        {"name": "panel_3", "type": "visualization", "id": "siem-top-hosts"},
    ]
    put_saved_object(
        "dashboard", "siem-hybrid-overview",
        {
            "title": "SIEM Hybrid Overview",
            "description": "Overview dashboard for App/WAF Filebeat logs ingested through OpenStack VPN Logstash.",
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({"useMargins": True, "syncColors": False,
                                       "syncCursor": True, "syncTooltips": True,
                                       "hidePanelTitles": False}),
            "timeRestore": False,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({"query": {"query": "", "language": "kuery"}, "filter": []})
            },
        },
        references,
    )
    print("  dashboard: SIEM Hybrid Overview")


# ─── Alert Rules ──────────────────────────────────────────────────────────────

def find_rule_id(name):
    q = urllib.parse.urlencode({"search": name, "search_fields": "name"})
    result = request("GET", f"/api/alerting/rules/_find?{q}")
    for item in result.get("data", []):
        if item.get("name") == name:
            return item.get("id")
    return None


def upsert_rule(body):
    rule_id = find_rule_id(body["name"])
    if rule_id:
        request("DELETE", f"/api/alerting/rule/{rule_id}", expected=(200, 204))
    return request("POST", "/api/alerting/rule", body, expected=(200, 201))


def create_alert_rules():
    rules = [
        {
            "name": "SIEM – No logs in 10 minutes",
            "tags": ["siem", "hybrid", "filebeat"],
            "rule_type_id": ".index-threshold",
            "consumer": "stackAlerts",
            "schedule": {"interval": "1m"},
            "params": {
                "index": [IDX_ALL], "timeField": "@timestamp",
                "aggType": "count", "groupBy": "all",
                "thresholdComparator": "<", "threshold": [1],
                "timeWindowSize": 10, "timeWindowUnit": "m",
            },
            "actions": [],
            "notify_when": "onActionGroupChange",
        },
        {
            "name": "SIEM – WAF 403 Attack Burst",
            "tags": ["siem", "waf", "security", "attack"],
            "rule_type_id": ".index-threshold",
            "consumer": "stackAlerts",
            "schedule": {"interval": "1m"},
            "params": {
                "index": [IDX_WAF], "timeField": "@timestamp",
                "aggType": "count", "groupBy": "all",
                "termField": "status_code", "termSize": 1,
                "thresholdComparator": ">", "threshold": [10],
                "timeWindowSize": 5, "timeWindowUnit": "m",
                "filterKuery": "status_code: 403",
            },
            "actions": [],
            "notify_when": "onActionGroupChange",
        },
        {
            "name": "SIEM – High 5xx Error Rate",
            "tags": ["siem", "waf", "health", "error"],
            "rule_type_id": ".index-threshold",
            "consumer": "stackAlerts",
            "schedule": {"interval": "1m"},
            "params": {
                "index": [IDX_WAF], "timeField": "@timestamp",
                "aggType": "count", "groupBy": "all",
                "thresholdComparator": ">", "threshold": [5],
                "timeWindowSize": 5, "timeWindowUnit": "m",
                "filterKuery": "status_code >= 500",
            },
            "actions": [],
            "notify_when": "onActionGroupChange",
        },
    ]
    for rule in rules:
        upsert_rule(rule)
        print(f"  alert rule: {rule['name']}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("Creating data views...")
    create_data_views()

    print("Creating WAF security dashboard...")
    create_waf_dashboard()

    print("Creating service health dashboard...")
    create_health_dashboard()

    print("Creating response operations dashboard...")
    create_response_dashboard()

    print("Creating overview dashboard...")
    create_overview_dashboard()

    print("Creating alert rules...")
    create_alert_rules()

    print("\nDone.")
    print(f"  WAF dashboard:    {KIBANA_URL}/app/dashboards#/view/siem-waf-security")
    print(f"  Health dashboard: {KIBANA_URL}/app/dashboards#/view/siem-service-health")
    print(f"  Response:         {KIBANA_URL}/app/dashboards#/view/siem-response-operations")
    print(f"  Overview:         {KIBANA_URL}/app/dashboards#/view/siem-hybrid-overview")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
