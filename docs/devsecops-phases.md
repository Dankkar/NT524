# Các Giai Đoạn DevSecOps Trong Dự Án

Ngày cập nhật: 2026-05-30

Tài liệu này mô tả dự án đang tập trung vào những giai đoạn nào trong vòng đời
DevSecOps, và cách các khối `Monitoring`, `Logging`, `Detect`, `Response`,
`Recover` liên kết với kiến trúc hybrid cloud hiện tại.

## Trọng Tâm DevSecOps

Dự án tập trung mạnh nhất vào các giai đoạn runtime/operations:

```text
Deploy -> Operate -> Monitor -> Detect -> Response -> Recover
```

Trọng tâm không nằm ở việc phát triển một ứng dụng nghiệp vụ lớn. Ứng dụng Flask
trong repo chủ yếu là workload nhẹ để kiểm tra xác thực, WAF, database,
logging và failover. Giá trị chính của dự án nằm ở việc đưa
workload đó vào một kiến trúc hybrid cloud có:

- Public DNS failover bằng Route 53.
- Access Gateway + Amazon Cognito + oauth2-proxy.
- WAF ModSecurity/OWASP CRS ở cả AWS và OpenStack.
- PostgreSQL primary trên AWS; OpenStack app truy cập DB qua WAF/VPN để giám sát flow.
- WireGuard site-to-site VPN.
- Filebeat -> Logstash -> Elasticsearch -> Kibana.
- Feedback API và ML/rule tuning loop cho WAF.

| Stage | Mức độ tập trung | Trong dự án này |
| --- | --- | --- |
| Code | Thấp | App Flask chỉ là ứng dụng demo để tạo traffic và kiểm tra auth/WAF/DB. |
| Build | Trung bình | Có Docker image cho app và WAF. GitHub Actions cũ đã bỏ; image/rule update vận hành bằng local tooling và Ansible. |
| Test | Trung bình | Có test login, Sign Out, WAF SQLi/XSS, VPN, DB flow OpenStack app -> AWS DB và Route 53 failover/failback. Chưa phải full penetration testing framework. |
| Release | Trung bình | Terraform/Ansible đưa cấu hình ra AWS và OpenStack. Rule WAF sau feedback/ML được release bằng Ansible `waf.yml --tags update_rules`. |
| Deploy | Cao | Terraform tạo cloud resources; Ansible deploy gateway, oauth2-proxy, WAF, app, DB, VPN, Filebeat và Logstash. |
| Operate | Cao | User truy cập `app.nt524.io.vn`; gateway bắt buộc login; WAF bảo vệ app; cả AWS app và OpenStack app đọc/ghi AWS DB primary. |
| Monitor | Cao | Theo dõi DNS, gateway, auth, WAF, app, PostgreSQL, VPN và SIEM pipeline. |
| Detect | Cao | WAF/OWASP CRS detect attack; SIEM detect lỗi/auth/infra bất thường; ML hỗ trợ review payload và rule tuning. |
| Response | Cao | WAF block, Route 53 failover, restart service/VPN, Feedback API label payload, export tuned WAF rules. |
| Recover | Trung bình | Route 53 failover/failback giữa AWS và OpenStack; DB hiện là single-primary trên AWS nên recover DB tập trung vào khôi phục AWS DB, không promote OpenStack DB. |
| Audit/Compliance | Thấp/Trung bình | Có log làm bằng chứng vận hành và điều tra, nhưng chưa phải compliance framework đầy đủ. |
| Threat Intelligence | Thấp | Hiện dùng OWASP CRS và log nội bộ; chưa tích hợp threat intel feed bên ngoài. |

Khi được hỏi "ML nằm ở phase nào?", câu trả lời đúng là:

```text
ML nằm chủ yếu ở Detect và Response.

Detect:
  Dùng WAF/audit log và dataset feedback để hỗ trợ phân loại payload,
  review false positive và đánh giá rule nào quá chặt/quá lỏng.

Response:
  Dùng kết quả feedback/ML để sinh hoặc tune rule cho WAF,
  sau đó deploy lại cho AWS WAF và OpenStack WAF.
```

Lưu ý: ML trong dự án này không thay thế WAF. WAF vẫn là lớp enforce/block trực
tiếp. ML là lớp hỗ trợ phân tích, feedback và rule tuning.

## Monitoring

Monitoring giúp biết hệ thống đang sống hay chết, lỗi nằm ở lớp nào và khi nào
cần response. Monitoring ưu tiên metric, health state, trạng thái dịch vụ và
alert signal; không nhất thiết lưu toàn bộ chi tiết request.

| Thành phần | Cần monitor | Ảnh hưởng tới các phase sau |
| --- | --- | --- |
| DNS/Route 53 | `app.nt524.io.vn` resolve về AWS hay OpenStack; health check `/healthz`; thời gian failover/failback | Nếu AWS gateway/app path fail thì Response là failover sang OpenStack; Recover là failback về AWS khi primary khỏe lại. |
| Cognito/oauth2-proxy | Redirect login, callback `/oauth2/callback`, Sign Out `/oauth2/sign_out`, tỷ lệ 401/403/502, service status | Nếu callback/token exchange/logout lỗi thì Detect auth incident và Response là sửa oauth2-proxy/Cognito config hoặc restart gateway. |
| Gateway | Nginx active, HTTP status rate, latency gateway -> WAF, `/healthz`, connection count | Nếu gateway down thì Route 53 failover; nếu 5xx tăng thì điều tra WAF/app/DB. |
| WAF | Container/service status, request rate, 403 rate, 5xx rate, top rule/source IP, ModSecurity error log | Nếu 403 tăng đột biến thì Detect attack burst; Response là block/tune rule/review false positive. |
| App | `/healthz`, latency, 5xx, container status, DB connection health | `/healthz` chạm DB bằng `select 1`, nên nếu app hoặc DB path lỗi thì health fail thay vì "sống giả". |
| PostgreSQL AWS primary | TCP/5432 reachable, `pg_is_in_recovery() = f`, active connections, disk usage | Nếu primary lỗi, app plane bị ảnh hưởng; Response là khôi phục AWS DB hoặc restore từ backup/snapshot. |
| OpenStack app -> AWS DB flow | Log prefix `OPENSTACK_APP_TO_AWS_DB`, `SRC=10.0.1.214`, `DST=172.31.3.61`, `DPT=5432`, index `siem-db-flow-*` | Xác nhận request DB từ OpenStack app đi qua OpenStack WAF/VPN và chỉ flow tới AWS DB được monitor/log/detect. |
| VPN/WireGuard | `wg-quick@wg0`, latest handshake, peer reachability, packet loss, latency, bytes sent/received, TCP MSS clamp | Nếu VPN down thì OpenStack app mất đường tới AWS DB primary, AWS Filebeat không gửi được về Logstash OpenStack. |
| SIEM pipeline | Filebeat active, Logstash active/listen `10.0.2.254:5044`, Elasticsearch health, Kibana reachable, ingest rate | Nếu pipeline chết thì Detect/Response mất dữ liệu; Response là restart Filebeat/Logstash/ELK và kiểm tra disk/heap/index. |

Monitoring nên được hiển thị bằng Kibana dashboards:

- `SIEM Hybrid Overview`: log volume theo thời gian, host và role.
- `Service Health - Load & Error Monitoring`: request throughput, 5xx, log volume, syslog high severity.
- `WAF Security - Attack & False Positive Review`: WAF 403, top blocked IP/path/rule.
- `Response Operations - WAF/Auth/Infra`: sự kiện cần response như WAF block burst, auth issue, 5xx, syslog lỗi.

## Logging

Logging lưu lại bằng chứng chi tiết để điều tra, detect và làm dữ liệu cho
feedback/ML. Logging là đầu vào trực tiếp cho Detect.

| Nguồn log | Nên log | Không nên log |
| --- | --- | --- |
| Gateway Nginx | Client IP, method, path, status, user agent, auth callback request, gateway error log | Raw cookie session, token, password |
| oauth2-proxy | Auth success/failure, `/oauth2/auth`, `/oauth2/callback`, `/oauth2/sign_out`, session/state error | ID token, access token, refresh token raw |
| WAF/ModSecurity | Access log, error/audit log, `403`, rule id, rule message, path, method, source IP, payload bị block đã mask nếu cần | Dữ liệu nhạy cảm đầy đủ trong body |
| App | Access/error log, exception, DB timeout, DB connection refused, request đã qua auth | Password, token, full sensitive DB record |
| PostgreSQL | Failed auth, slow query, error, connection timeout, backup/restore status nếu cấu hình thêm | Query/body chứa thông tin nhạy cảm nếu không cần |
| VPN/system | Interface up/down, handshake timeout, route/firewall/NAT error, peer reachability | Packet payload trong VPN |
| Route 53/failover | Health check status, thời điểm failover/failback nếu tích hợp thêm log/metric | Không áp dụng |
| Feedback/ML | Payload id/hash, label legitimate/malicious, reviewer, dataset version, rule export version | Token/user secret |

Pipeline logging hiện tại trong repo:

```text
Filebeat trên gateway/WAF/app/VPN nodes
-> Logstash trên OpenStack VPN node 10.0.2.254:5044
-> Elasticsearch trên 172.10.10.1:9200
-> Kibana dashboards trên 127.0.0.1:5601
```

Các index chính:

```text
siem-gateway-access-YYYY.MM.dd
siem-waf-access-YYYY.MM.dd
siem-app-access-YYYY.MM.dd
siem-syslog-YYYY.MM.dd
siem-hybrid-YYYY.MM.dd
```

Lưu ý về thứ tự log: một request SQLi có thể sinh nhiều log gần như cùng lúc:

```text
oauth2-proxy auth check -> WAF ModSecurity error -> WAF access 403 -> gateway access 403
```

Kibana có thể hiển thị thứ tự hơi lệch do timestamp parsing và ingest delay,
đặc biệt giữa WAF access log và ModSecurity error log.

## Detect

Detect dùng dữ liệu từ Monitoring và Logging để xác định sự kiện bất thường. Có
bốn nhóm detect chính:

| Nhóm detect | Đầu vào | Điều cần detect | Output |
| --- | --- | --- | --- |
| Web attack | WAF access/error logs | SQLi, XSS, path traversal, command injection, endpoint scan, 403 burst | Source IP, path, rule id, severity, transaction/log detail |
| Auth abuse | Gateway/oauth2-proxy/Cognito logs | Login fail nhiều lần, callback lỗi, state mismatch, session error, request chưa auth lặp lại | User/email nếu có, IP, endpoint, count, thời gian |
| Infra failure | DNS health, gateway/app health, DB/VPN monitor, syslog | Gateway down, WAF/app down, AWS DB unreachable, VPN mất handshake, Route 53 failover | Component, site AWS/OpenStack, start/end time |
| ML/rule tuning | WAF blocked payload, feedback dataset | False positive, payload nghi ngờ, rule quá chặt/quá lỏng | Label dự đoán, score, rule cần tune, item cần review |

Với false negative, cần có nguồn ground truth hoặc nhãn từ bên ngoài cho những
request WAF đã allow nhưng sau đó được xác định là malicious. Vì vậy trong repo
hiện tại, ML phù hợp nhất cho false positive review và WAF rule tuning.

Luồng ML/WAF:

```text
WAF block/allow
-> log vào SIEM
-> Feedback API label
-> dataset
-> ML train/export
-> tuned WAF rule
-> Ansible deploy rule cho AWS WAF và OpenStack WAF
```

Chi tiết endpoint và cách vận hành Feedback API nằm trong
`docs/feedback-api.md`.

## Response

Response là hành động sau khi Detect. Dự án nên tách response thành tự động và
bán tự động/thủ công.

| Sự kiện | Response tự động | Response bán tự động/thủ công |
| --- | --- | --- |
| Web attack bị WAF match | WAF trả `403`, ghi WAF access/error log, đẩy SIEM event | Review payload; nếu false positive thì label qua Feedback API và tune rule |
| 403 burst từ một IP | WAF tiếp tục block; dashboard/alert có thể hiển thị spike | Xác minh scanner/attack thật; nếu cần thêm denylist tạm thời ở WAF/gateway |
| Auth callback/session/logout lỗi | Gateway chặn request chưa auth hoặc không clear session đúng | Kiểm tra oauth2-proxy config, whitelist domain, cookie secret, callback/logout URL, Cognito client |
| AWS gateway/app path down | Route 53 failover sang OpenStack gateway | Restart nginx/oauth2-proxy/app/WAF; kiểm tra SG/EIP/health check |
| AWS hồi phục | Route 53 failback về AWS primary | Xác nhận traffic quay về AWS và OpenStack vẫn healthy secondary |
| VPN down | Alert/no DB flow log nếu có monitoring | Kiểm tra WAN IP, AWS SG UDP/51820, WireGuard handshake, route/NAT, TCP MSS clamp |
| AWS DB primary unreachable | App `/healthz` fail; Route 53 có thể failover app path nếu AWS path fail | Restart AWS DB hoặc restore từ backup/snapshot; không ghi sang OpenStack DB vì topology đã bỏ DB này. |
| OpenStack app -> AWS DB flow mất log | OpenStack app vẫn tạo request nhưng `siem-db-flow-*` không tăng | Kiểm tra iptables LOG trên OpenStack WAF, rsyslog, Filebeat, Logstash và route qua VPN. |
| SIEM pipeline down | Alert/no logs nếu có monitoring | Restart Filebeat/Logstash/ELK; kiểm tra Elasticsearch disk/heap/index |
| False positive WAF | Không auto allow ngay | Feedback API label legitimate, ML/rule export, test lại, deploy rule bằng Ansible |

Response loop cho ML/WAF:

```text
1. WAF block request và ghi log.
2. SIEM dashboard hiển thị blocked request detail.
3. Admin review trong Feedback API.
4. Payload được label legitimate/malicious.
5. Dataset cập nhật.
6. ML pipeline retrain/export tuned rule.
7. Rule mới deploy vào AWS WAF và OpenStack WAF bằng Ansible `waf.yml --tags update_rules`.
8. Monitor lại 403 rate và false positive sau khi deploy.
```

## Recover

Recover trong dự án gồm hai lớp: recover app path và recover database.

### Route 53 Failover/Failback

Khi AWS gateway/app path fail:

```text
Route 53 health check /healthz fail
-> DNS chuyển app.nt524.io.vn sang OpenStack gateway
-> user đi qua OpenStack gateway -> OpenStack WAF -> OpenStack app
```

Trong trạng thái bình thường, kể cả khi traffic vào OpenStack app, app vẫn dùng
AWS DB primary qua VPN:

```text
OpenStack app -> OpenStack WAF -> OpenStack VPN -> AWS VPN -> AWS DB primary
```

Khi AWS hồi phục:

```text
Route 53 health check pass lại
-> DNS failback về AWS gateway
```

### Database Recovery

PostgreSQL hiện chạy theo mô hình single-primary trên AWS:

```text
AWS DB primary 172.31.3.61
```

OpenStack DB đã được loại khỏi topology, nên không còn DB thứ hai và
không còn promote DB sang OpenStack. OpenStack app vẫn đọc/ghi AWS DB primary,
nhưng request DB phải đi qua WAF/VPN để có log:

```text
OpenStack App 10.0.1.214
  -> OpenStack WAF 10.0.1.254 / 10.0.2.10
  -> OpenStack VPN 10.0.2.254
  -> WireGuard 10.200.0.2 <-> 10.200.0.1
  -> AWS DB 172.31.3.61:5432
```

WAF chỉ log/detect request có target là AWS DB TCP/5432:

```text
/var/log/openstack-db-flow.log
siem-db-flow-YYYY.MM.dd
tag: openstack_app_to_aws_db
```

## Kết Luận Ngắn Gọn

Dự án là một lab DevSecOps thiên về runtime security cho hybrid cloud.

```text
Deploy/Operate:
  Đưa app vào AWS + OpenStack với AAA, WAF, VPN, PostgreSQL primary trên AWS.

Monitor/Logging:
  Thu health, metric và log từ gateway, oauth2-proxy, WAF, app, DB, VPN và SIEM.

Detect:
  Dùng WAF, SIEM và ML-support để phát hiện attack, auth abuse và lỗi hạ tầng.

Response:
  WAF block, DNS failover, restart service/VPN, Feedback API, ML-tuned WAF rules.

Recover:
  Failback về AWS, khôi phục VPN/DB/service, controlled DB failover khi cần.
```

Vì vậy, nếu đặt dự án vào hình vòng lặp DevSecOps, phần nổi bật nhất là:

```text
Deploy -> Operate -> Monitor -> Detect -> Response -> Recover
```
