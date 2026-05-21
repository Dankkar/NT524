import json
import urllib.request
import urllib.parse
import re
import os

ES_URL = "http://172.10.10.1:9200/siem-hybrid-*/_search"
DATASET_DIR = os.path.join(os.path.dirname(__file__), "../data/dataset")

def fetch_es_logs():
    query = {
        "size": 5000,
        "query": {
            "bool": {
                "must": [
                    {"term": {"fields.node_role": "waf"}},
                    {"term": {"fields.log_type": "docker_container"}}
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
    
    try:
        with urllib.request.urlopen(req) as res:
            response_data = json.loads(res.read().decode("utf-8"))
            return response_data.get("hits", {}).get("hits", [])
    except Exception as e:
        print(f"[ERROR] Failed to query Elasticsearch: {e}")
        return []

def parse_nginx_log(log_message):
    # Regex to parse Nginx standard access log format:
    # 171.248.116.219 - - [21/May/2026:10:21:45 +0000] "GET /path?query HTTP/1.1" 200 123 "-" "User-Agent"
    pattern = r'^(\S+) - \S+ \[(.*?)\] "(\S+) (\S+) \S+" (\d+) (\d+)'
    match = re.match(pattern, log_message)
    if not match:
        return None
        
    client_ip = match.group(1)
    timestamp = match.group(2)
    method = match.group(3)
    request_uri = match.group(4)
    status_code = int(match.group(5))
    
    return {
        "client_ip": client_ip,
        "timestamp": timestamp,
        "method": method,
        "request_uri": request_uri,
        "status": status_code
    }

def extract_payload_from_uri(uri):
    parsed = urllib.parse.urlparse(uri)
    query_string = parsed.query
    if not query_string:
        return None
    # Decode URL-encoded characters
    try:
        decoded = urllib.parse.unquote(query_string)
        return decoded
    except Exception:
        return query_string

def main():
    print("[INFO] Fetching logs from Elasticsearch...")
    hits = fetch_es_logs()
    print(f"[INFO] Retrieved {len(hits)} raw log entries.")
    
    legitimate_payloads = []
    malicious_payloads = []
    
    for hit in hits:
        source = hit.get("_source", {})
        message_raw = source.get("message", "")
        
        # Log is stored inside a JSON string under message: {"log": "...", "stream": "stdout"}
        try:
            message_json = json.loads(message_raw)
            log_line = message_json.get("log", "").strip()
        except Exception:
            log_line = message_raw.strip()
            
        parsed = parse_nginx_log(log_line)
        if not parsed:
            continue
            
        payload = extract_payload_from_uri(parsed["request_uri"])
        if not payload:
            continue
            
        status = parsed["status"]
        if status == 403:
            malicious_payloads.append(payload)
        elif status == 200:
            legitimate_payloads.append(payload)
            
    print(f"[INFO] Parsed {len(legitimate_payloads)} legitimate payloads and {len(malicious_payloads)} malicious payloads.")
    
    os.makedirs(DATASET_DIR, exist_ok=True)
    
    legitimate_path = os.path.join(DATASET_DIR, "legitimate_train.json")
    malicious_path = os.path.join(DATASET_DIR, "malicious_train.json")
    
    # Load existing to resolve conflicts and avoid duplication
    existing_legitimate = set()
    existing_malicious = set()
    
    if os.path.exists(legitimate_path):
        try:
            with open(legitimate_path, "r") as f:
                existing_legitimate = set(json.load(f))
        except Exception:
            pass
            
    if os.path.exists(malicious_path):
        try:
            with open(malicious_path, "r") as f:
                existing_malicious = set(json.load(f))
        except Exception:
            pass
            
    # Merge new extractions with existing sets
    merged_legitimate = existing_legitimate.union(set(legitimate_payloads))
    merged_malicious = existing_malicious.union(set(malicious_payloads))
    
    # Resolve conflicts:
    # 1. Human manual decision is prioritized. If marked legitimate, remove from malicious
    merged_malicious = merged_malicious.difference(existing_legitimate)
    
    # 2. If marked malicious, remove from legitimate
    merged_legitimate = merged_legitimate.difference(existing_malicious)
    
    # 3. For any remaining overlap from new logs, treat as malicious if blocked (403)
    overlap = merged_legitimate.intersection(merged_malicious)
    merged_legitimate = merged_legitimate.difference(overlap)
    
    with open(legitimate_path, "w") as f:
        json.dump(list(merged_legitimate), f, indent=4)
        
    with open(malicious_path, "w") as f:
        json.dump(list(merged_malicious), f, indent=4)
        
    print(f"[SUCCESS] Dataset updated. Legitimate: {len(merged_legitimate)}, Malicious: {len(merged_malicious)} total.")


if __name__ == "__main__":
    main()
