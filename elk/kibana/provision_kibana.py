#!/usr/bin/env python3
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


KIBANA_URL = "http://127.0.0.1:5601"
DATA_VIEW_ID = "siem-hybrid-data-view"
DASHBOARD_ID = "siem-hybrid-overview"
RULE_NAME = "SIEM Hybrid - no logs in 10 minutes"


def request(method, path, body=None, expected=(200, 201)):
    data = None
    headers = {"kbn-xsrf": "true"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        f"{KIBANA_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = response.read().decode("utf-8")
            if response.status not in expected:
                raise RuntimeError(f"{method} {path} returned {response.status}: {payload}")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        if exc.code not in expected:
            raise RuntimeError(f"{method} {path} returned {exc.code}: {payload}") from exc
        return json.loads(payload) if payload else {}


def put_saved_object(obj_type, obj_id, attributes, references=None):
    return request(
        "POST",
        f"/api/saved_objects/{obj_type}/{obj_id}?overwrite=true",
        {
            "attributes": attributes,
            "references": references or [],
        },
    )


def create_data_view():
    body = {
        "data_view": {
            "id": DATA_VIEW_ID,
            "title": "siem-hybrid-*",
            "name": "SIEM Hybrid Logs",
            "timeFieldName": "@timestamp",
        },
        "override": True,
    }
    return request("POST", "/api/data_views/data_view", body, expected=(200, 201))


def vega_vis(title, spec):
    return {
        "title": title,
        "visState": json.dumps(
            {
                "title": title,
                "type": "vega",
                "params": {"spec": json.dumps(spec)},
                "aggs": [],
            }
        ),
        "uiStateJSON": "{}",
        "description": "",
        "version": 1,
        "kibanaSavedObjectMeta": {"searchSourceJSON": "{}"},
    }


def create_visualizations():
    base_time_query = {
        "range": {
            "@timestamp": {
                "gte": "now-24h",
                "lte": "now",
            }
        }
    }

    over_time = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": "Events over time",
        "data": {
            "url": {
                "index": "siem-hybrid-*",
                "body": {
                    "size": 0,
                    "query": base_time_query,
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
            "y": {"field": "doc_count", "type": "quantitative", "title": "Events"},
        },
    }

    by_role = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": "Events by node role",
        "data": {
            "url": {
                "index": "siem-hybrid-*",
                "body": {
                    "size": 0,
                    "query": base_time_query,
                    "aggs": {
                        "roles": {
                            "terms": {
                                "field": "fields.node_role.keyword",
                                "size": 10,
                            }
                        }
                    },
                },
            },
            "format": {"property": "aggregations.roles.buckets"},
        },
        "mark": {"type": "bar", "tooltip": True},
        "encoding": {
            "x": {"field": "key", "type": "nominal", "title": "Role"},
            "y": {"field": "doc_count", "type": "quantitative", "title": "Events"},
            "color": {"field": "key", "type": "nominal", "legend": None},
        },
    }

    top_hosts = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": "Top hosts",
        "data": {
            "url": {
                "index": "siem-hybrid-*",
                "body": {
                    "size": 0,
                    "query": base_time_query,
                    "aggs": {
                        "hosts": {
                            "terms": {
                                "field": "host.name.keyword",
                                "size": 10,
                            }
                        }
                    },
                },
            },
            "format": {"property": "aggregations.hosts.buckets"},
        },
        "mark": {"type": "bar", "tooltip": True},
        "encoding": {
            "y": {"field": "key", "type": "nominal", "title": "Host", "sort": "-x"},
            "x": {"field": "doc_count", "type": "quantitative", "title": "Events"},
            "color": {"field": "key", "type": "nominal", "legend": None},
        },
    }

    objects = {
        "siem-events-over-time": ("SIEM Hybrid - Events over time", over_time),
        "siem-events-by-role": ("SIEM Hybrid - Events by role", by_role),
        "siem-top-hosts": ("SIEM Hybrid - Top hosts", top_hosts),
    }
    for obj_id, (title, spec) in objects.items():
        put_saved_object("visualization", obj_id, vega_vis(title, spec))


def create_dashboard():
    panels = [
        {
            "version": "8.13.0",
            "gridData": {"x": 0, "y": 0, "w": 48, "h": 15, "i": "1"},
            "panelIndex": "1",
            "embeddableConfig": {},
            "panelRefName": "panel_1",
        },
        {
            "version": "8.13.0",
            "gridData": {"x": 0, "y": 15, "w": 24, "h": 15, "i": "2"},
            "panelIndex": "2",
            "embeddableConfig": {},
            "panelRefName": "panel_2",
        },
        {
            "version": "8.13.0",
            "gridData": {"x": 24, "y": 15, "w": 24, "h": 15, "i": "3"},
            "panelIndex": "3",
            "embeddableConfig": {},
            "panelRefName": "panel_3",
        },
    ]
    references = [
        {"name": "panel_1", "type": "visualization", "id": "siem-events-over-time"},
        {"name": "panel_2", "type": "visualization", "id": "siem-events-by-role"},
        {"name": "panel_3", "type": "visualization", "id": "siem-top-hosts"},
    ]
    attributes = {
        "title": "SIEM Hybrid Overview",
        "description": "Overview dashboard for App/WAF Filebeat logs ingested through OpenStack VPN Logstash.",
        "panelsJSON": json.dumps(panels),
        "optionsJSON": json.dumps(
            {
                "useMargins": True,
                "syncColors": False,
                "syncCursor": True,
                "syncTooltips": True,
                "hidePanelTitles": False,
            }
        ),
        "timeRestore": False,
        "kibanaSavedObjectMeta": {
            "searchSourceJSON": json.dumps(
                {"query": {"query": "", "language": "kuery"}, "filter": []}
            )
        },
    }
    put_saved_object("dashboard", DASHBOARD_ID, attributes, references)


def find_rule_id():
    query = urllib.parse.urlencode({"search": RULE_NAME, "search_fields": "name"})
    result = request("GET", f"/api/alerting/rules/_find?{query}")
    for item in result.get("data", []):
        if item.get("name") == RULE_NAME:
            return item.get("id")
    return None


def create_or_update_rule():
    body = {
        "name": RULE_NAME,
        "tags": ["siem", "hybrid", "filebeat"],
        "rule_type_id": ".index-threshold",
        "consumer": "stackAlerts",
        "schedule": {"interval": "1m"},
        "params": {
            "index": ["siem-hybrid-*"],
            "timeField": "@timestamp",
            "aggType": "count",
            "groupBy": "all",
            "thresholdComparator": "<",
            "threshold": [1],
            "timeWindowSize": 10,
            "timeWindowUnit": "m",
        },
        "actions": [],
        "notify_when": "onActionGroupChange",
    }
    rule_id = find_rule_id()
    if rule_id:
        request("DELETE", f"/api/alerting/rule/{rule_id}", expected=(200, 204))
    return request("POST", "/api/alerting/rule", body, expected=(200, 201))


def main():
    create_data_view()
    create_visualizations()
    create_dashboard()
    create_or_update_rule()
    print("Provisioned Kibana data view, dashboard, and alert rule.")
    print(f"Dashboard: {KIBANA_URL}/app/dashboards#/view/{DASHBOARD_ID}")
    print(f"Data view: {DATA_VIEW_ID}")
    print(f"Alert rule: {RULE_NAME}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
