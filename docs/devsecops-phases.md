# DevSecOps Phases For This Project

Ngay cap nhat: 2026-05-29

Tai lieu nay mo ta project dang tap trung vao phase nao trong DevSecOps va cach 4 buoc `Monitoring`, `Logging`, `Detect`, `Response` lien ket voi nhau.

## Trong Tam DevSecOps

Project nay tap trung manh nhat vao cac stage sau:

```text
Deploy -> Operate -> Monitor -> Detect -> Response -> Recover
```

Trong tam khong nam o viec code mot ung dung lon, ma nam o viec dua mot ung dung nhe vao kien truc hybrid cloud co access control, WAF, logging, SIEM, failover va feedback loop cho ML/WAF.

| Stage | Muc do tap trung | Trong project nay |
| --- | --- | --- |
| Code | Thap | App Flask chi la ung dung demo de tao traffic va kiem tra auth/WAF/DB. |
| Build | Trung binh | Co Docker image cho app/WAF. GitHub Actions cu da bo; build/push image WAF hien lam thu cong khi doi Dockerfile/base image. |
| Test | Trung binh | Test login, WAF SQLi, VPN, DB, failover/failback. Chua phai full penetration testing framework. |
| Release | Trung binh | Terraform/Ansible dua cau hinh ra AWS va OpenStack. Retrain rule ML duoc release bang Ansible `--tags update_rules`. |
| Deploy | Cao | Terraform tao cloud resources; Ansible deploy gateway, oauth2-proxy, WAF, app, DB, VPN, Logstash/Filebeat. |
| Operate | Cao | User vao `app.nt524.io.vn`; gateway enforce login; WAF bao ve app; app doc/ghi DB qua VPN. |
| Monitor | Cao | Theo doi DNS, gateway, auth, WAF, app, DB, VPN va SIEM pipeline. |
| Detect | Cao | WAF/OWASP CRS detect attack; SIEM detect loi va bat thuong; ML ho tro phan loai payload va false positive/false negative. |
| Response | Cao | WAF block, Route 53 failover, restart service/VPN, feedback API label payload, ML export tuned WAF rules. |
| Recover | Trung binh/Cao | Route 53 failover/failback giua AWS va OpenStack; can cai tien DB replica neu muon AWS doc lap khi OpenStack tat. |
| Audit/Compliance | Thap/Trung binh | Co log lam bang chung van hanh, nhung chua thanh compliance framework day du. |
| Threat Intelligence | Thap | Hien dung OWASP CRS va log noi bo; chua tich hop threat intel feed ben ngoai. |

Vi vay, khi duoc hoi "ML dung o phase nao", cau tra loi dung la:

```text
ML nam chu yeu o Detect va Response.
Detect: dung WAF/audit log va dataset feedback de phan loai payload, tim false positive/false negative.
Response: dung ket qua feedback/ML de sinh hoac tune rule cho WAF, sau do deploy lai cho AWS WAF va OpenStack WAF.
```

## Monitoring

Muc dich cua Monitoring la biet he thong dang song hay chet, loi o lop nao va khi nao can response. Monitoring khong can luu moi chi tiet request; no uu tien metric, health state va alert signal.

| Thanh phan | Can monitor | Anh huong toi cac phase sau |
| --- | --- | --- |
| DNS/Route 53 | `app.nt524.io.vn` resolve ve AWS hay OpenStack; health check `/healthz`; thoi gian failover/failback | Neu primary fail thi Response la failover; Recover la failback khi AWS hoi phuc. |
| Cognito/oauth2-proxy | Redirect login, callback `/oauth2/callback`, ti le 401/403/502, service status | Neu callback/token exchange loi thi Detect auth incident va Response restart/fix gateway config. |
| Gateway | Nginx active, HTTP status rate, latency gateway -> WAF, connection count | Neu gateway down thi Route 53 failover; neu 5xx tang thi dieu tra WAF/app. |
| WAF | Service/container status, request rate, 403 rate, 5xx rate, top rule/source IP | Neu 403 tang dot bien thi Detect attack burst; Response block/tune rule. |
| App | `/healthz`, latency, 5xx, container status, DB connection health | Neu app song nhung DB chet thi health nen fail de tranh "song gia". |
| PostgreSQL | TCP 5432 reachable tu AWS/OpenStack app, active connections, slow query, disk usage | Neu DB loi thi app plane bi anh huong; Response la restart/promote replica/alert. |
| VPN | `wg-quick@wg0`, latest handshake, ping peer, packet loss, latency, bytes sent/received | Neu VPN down thi AWS app mat duong toi OpenStack DB; Response restart tunnel/route/NAT. |
| SIEM pipeline | Filebeat active, Logstash active/listen 5044, Elasticsearch health, Kibana reachable, ingest rate | Neu pipeline chet thi Detect/Response mat du lieu; Response restart Filebeat/Logstash/ELK. |

Monitoring nen duoc hien thi bang Kibana dashboard:

- `Service Health - Load & Error Monitoring`: request throughput, 5xx, log volume, syslog high severity.
- `SIEM Hybrid Overview`: log volume theo thoi gian, host, role.
- `Response Operations - WAF/Auth/Infra`: su kien can response nhu WAF block burst, 5xx, syslog loi.

## Logging

Muc dich cua Logging la luu lai bang chung chi tiet de dieu tra, detect va lam du lieu cho feedback/ML. Logging la dau vao truc tiep cho Detect.

| Nguon log | Nen log | Khong nen log |
| --- | --- | --- |
| Gateway Nginx | client IP, method, path, status, upstream status, user agent, auth callback request, error log | raw cookie session, token, password |
| oauth2-proxy | auth success/failure, callback error, session/state error, upstream auth result | ID token, access token, refresh token raw |
| WAF/ModSecurity | access log, audit/error log, `403`, rule id, rule message, path, method, source IP, payload bi block da mask neu can | du lieu nhay cam day du trong body |
| App | access/error log, request da qua auth, exception, DB timeout, DB connection refused | password, token, full sensitive DB record |
| PostgreSQL | failed auth, slow query, error, connection timeout, schema change neu co | query/body chua thong tin nhay cam neu khong can |
| VPN/system | interface up/down, handshake timeout, route/firewall/NAT error, peer reachability | packet payload trong VPN |
| Route 53/failover | health check status, thoi diem failover/failback | khong ap dung |
| Feedback/ML | payload id/hash, label legitimate/malicious, reviewer, dataset version, rule export version | token/user secret |

Trong repo hien tai, pipeline chuan la:

```text
Filebeat on gateway/WAF/app/VPN nodes
-> Logstash on OpenStack VPN node :5044
-> Elasticsearch on 172.10.10.1:9200
-> Kibana dashboards on 127.0.0.1:5601
```

## Detect

Detect dung du lieu tu Monitoring va Logging de xac dinh su kien bat thuong. Co 4 nhom detect chinh:

| Nhom detect | Dau vao | Dieu can detect | Output |
| --- | --- | --- | --- |
| Web attack | WAF access/audit logs | SQLi, XSS, path traversal, command injection, scan endpoint, 403 burst | source IP, path, rule id, severity, transaction/log detail |
| Auth abuse | gateway/oauth2-proxy/Cognito logs | login fail nhieu lan, callback loi, state mismatch, session error, request khong auth lap lai | user/email neu co, IP, endpoint, count, thoi gian |
| Infra failure | DNS health, gateway/app health, DB/VPN monitor, syslog | gateway down, WAF/app down, DB unreachable, VPN mat handshake, Route 53 failover | component, site AWS/OpenStack, start/end time |
| ML anomaly/tuning | WAF blocked payload, feedback dataset | false positive, false negative, payload nghi ngo, rule qua chat/qua long | label du doan, score, rule can tune, item can review |

ML khong thay WAF trong project nay. ML dung nhu mot lop ho tro phan tich va tuning:

```text
WAF block/allow -> log vao SIEM -> Feedback API label -> dataset -> ML train/export -> tuned WAF rule
```

Chi tiet endpoint va cach van hanh Feedback API nam trong `docs/feedback-api.md`.

## Response

Response la hanh dong sau khi Detect. Project nen tach response thanh tu dong va ban tu dong:

| Su kien | Response tu dong | Response ban tu dong/thu cong |
| --- | --- | --- |
| Web attack bi WAF match | WAF tra `403`, ghi audit log, day SIEM event | review payload, neu false positive thi label qua Feedback API va tune rule |
| 403 burst tu mot IP | alert, co the them denylist tam thoi o WAF/gateway | xac minh co phai scanner/attack that khong |
| Auth callback/session loi | gateway chan request chua auth | kiem tra oauth2-proxy config, cookie secret, callback URL, Cognito client |
| AWS gateway down | Route 53 failover sang OpenStack | restart nginx/oauth2-proxy, kiem tra SG/EIP/health check |
| AWS hoi phuc | Route 53 failback ve AWS | xac nhan traffic quay ve primary |
| VPN down | alert, restart `wg-quick@wg0` neu dung automation | kiem tra WAN IP, SG UDP 51820, route/NAT |
| DB unreachable | app health fail, alert | restart DB, restore backup, hoac promote replica neu co |
| SIEM pipeline down | alert no logs, restart Filebeat/Logstash/ELK | kiem tra Elasticsearch disk/heap/index |
| False positive WAF | khong auto allow ngay | Feedback API label legitimate, ML/rule export, test lai, deploy rule |

Response loop cho ML/WAF:

```text
1. WAF block request va ghi log.
2. SIEM dashboard hien thi blocked request detail.
3. Admin review trong Feedback API.
4. Payload duoc label legitimate/malicious.
5. Dataset cap nhat.
6. ML pipeline retrain/export tuned rule.
7. Rule moi deploy vao AWS WAF va OpenStack WAF bang Ansible `waf.yml --tags update_rules`.
8. Monitor lai 403 rate va false positive sau khi deploy.
```

## Ket Luan Ngan Gon

Project nay la mot lab DevSecOps thien ve runtime security cho hybrid cloud. Trong tam la:

```text
Deploy/Operate: dua app vao AWS + OpenStack voi AAA, WAF, VPN, DB.
Monitor/Logging: thu health, metric va log tu gateway/WAF/app/DB/VPN/SIEM.
Detect: dung WAF, SIEM va ML de phat hien attack, auth abuse va loi ha tang.
Response: WAF block, DNS failover, restart service/VPN, feedback API va ML-tuned WAF rules.
Recover: failback ve AWS, khoi phuc VPN/DB/service sau su co.
```
