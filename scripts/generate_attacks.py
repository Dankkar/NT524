import sys
import time
import random
import urllib.request
import urllib.parse
import urllib.error

# WAF Public IP
WAF_IP = "54.254.229.116"

sqli_payloads = [
    "' OR 1=1 --",
    "admin' --",
    "' UNION SELECT null, null --",
    "' AND 1=0 UNION SELECT 1, 'admin', 'password' --",
    "' OR 'a'='a",
    "') OR ('a'='a",
    "1 AND 1=1",
    "1 OR 1=1",
    "1' ORDER BY 1--",
    "1' ORDER BY 2--",
    "1' ORDER BY 3--",
    "1' GROUP BY 1--",
    "' UNION SELECT username, password FROM users --",
    "' OR 1=1 LIMIT 1 --",
    "'; DROP TABLE users; --"
]

def send_request(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    count = 300
    if len(sys.argv) > 1:
        count = int(sys.argv[1])
        
    print(f"[INFO] Starting generation of {count} SQLi attack requests to http://{WAF_IP}...")
    blocked = 0
    for i in range(count):
        payload = random.choice(sqli_payloads)
        url = f"http://{WAF_IP}/rest/products/search?q={urllib.parse.quote(payload)}"
            
        res = send_request(url)
        if res == 403:
            blocked += 1
            
        if (i + 1) % 50 == 0:
            print(f"[PROGRESS] Sent {i+1}/{count} attacks. Blocked (403): {blocked}")
            
        time.sleep(0.02) # 20ms delay
        
    print(f"[COMPLETED] Total attacks sent: {count}. Blocked rate: {blocked}/{count}")

