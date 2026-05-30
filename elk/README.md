# Local SIEM Stack

Docker Compose stack for the hybrid SIEM lab.

- Elasticsearch listens on `172.10.10.1:9200` so Logstash on the OpenStack VPN node can write to it through the laptop AIO provider bridge.
- Kibana listens on `127.0.0.1:5601`.
- Logstash does not run in this compose stack. It is deployed by Ansible on the OpenStack VPN node.

Run:

```bash
sudo sysctl -w vm.max_map_count=262144
sudo docker compose up -d --remove-orphans
```

Logstash writes Filebeat events to daily indices. The current active index families are:

- `siem-gateway-access-YYYY.MM.dd`
- `siem-waf-access-YYYY.MM.dd`
- `siem-app-access-YYYY.MM.dd`
- `siem-syslog-YYYY.MM.dd`
- `siem-hybrid-YYYY.MM.dd` for uncategorized events.

Current dashboard provisioning creates:

- `SIEM Hybrid Overview`
- `Service Health - Load & Error Monitoring`
- `WAF Security - Attack & False Positive Review`
- `Response Operations - WAF/Auth/Infra`

The expected index families are:

- `siem-gateway-access-*`
- `siem-waf-access-*`
- `siem-app-access-*`
- `siem-syslog-*`
- `siem-hybrid-*`

Quick checks:

```bash
curl -fsS http://172.10.10.1:9200/_cluster/health
curl -fsS 'http://172.10.10.1:9200/_cat/indices/siem-*?h=index,docs.count,store.size&s=index'
```

Open dashboards:

```text
http://127.0.0.1:5601/app/dashboards#/view/siem-hybrid-overview
http://127.0.0.1:5601/app/dashboards#/view/siem-waf-security
http://127.0.0.1:5601/app/dashboards#/view/siem-service-health
http://127.0.0.1:5601/app/dashboards#/view/siem-response-operations
```

To generate WAF/security events for the dashboard, send blocked payloads through the public gateway:

```bash
curl -k -o /dev/null -s -w "%{http_code}\n" \
  "https://app.nt524.io.vn/?id=1%20OR%201=1"

curl -k -o /dev/null -s -w "%{http_code}\n" \
  "https://app.nt524.io.vn/?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E"
```

Expected result is usually `403`. These requests appear in `siem-waf-access-*` with tag `waf_blocked` when parsed by Logstash.
