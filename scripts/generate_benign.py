import sys
import time
import random
import urllib.request
import urllib.parse
import urllib.error

# WAF Public IP
WAF_IP = "3.1.159.30"

paths = [
    "/",
    "/api/Products",
    "/api/Challenges",
    "/rest/admin/application-version",
    "/assets/public/images/padding/1.jpg",
    "/assets/public/images/padding/2.jpg",
    "/assets/public/images/padding/3.jpg",
    "/assets/public/images/padding/4.jpg",
]

search_queries = [
    "apple", "banana", "juice", "orange", "glass", "mug", "shirt", "card", "sticker", "bag",
    "box", "cup", "bottle", "plate", "fork", "knife", "spoon", "bowl", "napkin", "towel"
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
    count = 1000
    if len(sys.argv) > 1:
        count = int(sys.argv[1])
        
    print(f"[INFO] Starting generation of {count} benign requests to http://{WAF_IP}...")
    success = 0
    for i in range(count):
        choice = random.choice(["path", "search"])
        if choice == "path":
            path = random.choice(paths)
            url = f"http://{WAF_IP}{path}"
        else:
            query = random.choice(search_queries)
            url = f"http://{WAF_IP}/rest/products/search?q={urllib.parse.quote(query)}"
            
        res = send_request(url)
        if isinstance(res, int) and res < 400:
            success += 1
            
        if (i + 1) % 100 == 0:
            print(f"[PROGRESS] Sent {i+1}/{count} requests. Success: {success}")
            
        time.sleep(0.01) # 10ms delay
        
    print(f"[COMPLETED] Total requests sent: {count}. Success rate: {success}/{count}")
