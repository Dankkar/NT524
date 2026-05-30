# Tổng hợp hướng đồ án Capstone

Ngày tổng hợp: 2026-05-30

## 1. Kết luận nhanh

Project hiện tại **không nên trình bày là làm trọn vẹn một capstone Zero Trust/Hybrid Cloud**, vì phạm vi đó quá rộng. Cách đóng gói hợp lý hơn là chọn một lát cắt cụ thể trong theme capstone:

> **Runtime Security và Feedback-Driven WAF Tuning cho Hybrid Cloud AWS + OpenStack**

Tên project đề xuất:

> **Hybrid Cloud Runtime Security: Access Gateway, WAF, SIEM và ML-assisted Rule Tuning trên AWS + OpenStack**

Tên ngắn cho slide:

> **Hybrid Cloud WAF-SIEM Feedback Loop**

Theme capstone phù hợp nhất:

- **Theme chính:** Đề tài 9 - Xây dựng hệ thống SIEM trên cloud.
- **Phần mở rộng có kiểm soát:** Đề tài 10 - Ứng dụng ML phát hiện/tuning từ logs.
- **Liên quan phụ:** Đề tài 1 - Zero Trust Hybrid Cloud, nhưng chỉ lấy phần identity-aware gateway, WAF, segmentation bằng gateway/security group/VPN; không làm full Zero Trust như SPIFFE/SPIRE, service mesh, OPA, device posture.

## 2. Vấn đề đặt ra

Trong môi trường hybrid cloud, ứng dụng có thể chạy trên cả AWS và OpenStack, nhưng các rủi ro runtime thường nằm ở các điểm sau:

- Người dùng có thể bypass auth/WAF nếu entrypoint và network rule không chặt.
- Logs bị phân tán trên gateway, WAF, app, VPN, DB và nhiều node cloud.
- WAF/OWASP CRS chặn được attack như SQLi, nhưng có thể sinh false positive hoặc false negative.
- Khi AWS path lỗi, hệ thống cần failover sang OpenStack mà vẫn giữ dữ liệu ứng dụng.
- Operator cần một vòng lặp từ detect đến response: xem log, review payload, label, tune rule, deploy lại WAF.

Câu hỏi nghiên cứu/thực nghiệm nên dùng:

> Làm sao thiết kế và triển khai một runtime security pipeline cho hybrid cloud, trong đó traffic đi qua access gateway và WAF, logs được tập trung vào SIEM, attack được detect, và feedback của operator được dùng để tune WAF rule?

## 3. Mục tiêu đồ án

Mục tiêu chính:

1. Triển khai kiến trúc hybrid cloud AWS + OpenStack có một entrypoint chung.
2. Bắt buộc user đi qua access gateway, OIDC/Cognito, WAF, rồi mới đến app.
3. Thu log từ gateway, WAF, app và VPN về ELK/SIEM.
4. Phát hiện request bị WAF block, đặc biệt SQLi/test payload.
5. Cung cấp Feedback API để operator label payload là legitimate hoặc malicious.
6. Dùng dataset feedback để retrain/export tuned ModSecurity rule.
7. Deploy rule mới lại AWS WAF và OpenStack WAF bằng Ansible.
8. Chứng minh failover/failback bằng Route 53 giữa AWS gateway và OpenStack gateway.

Ngoài phạm vi:

- Không làm full Zero Trust Architecture.
- Không làm full DL IDS hoặc threat hunting platform.
- Không làm CI/CD DevSecOps shift-left đầy đủ.
- Không giải quyết high availability database hoàn chỉnh; DB hiện centralized ở OpenStack.

## 4. Kiến trúc hiện tại

Luồng người dùng:

```text
User
-> app.nt524.io.vn
-> Route 53 Failover DNS
-> AWS Gateway hoặc OpenStack Gateway
-> Cognito / oauth2-proxy auth
-> Nginx Gateway
-> WAF Nginx + ModSecurity + OWASP CRS
-> Lightweight Flask App
-> PostgreSQL centralized trên OpenStack
```

Luồng logging và response:

```text
Gateway/WAF/App/VPN logs
-> Filebeat
-> Logstash
-> Elasticsearch
-> Kibana dashboards
-> Feedback API
-> Label payload
-> Dataset update
-> ML retrain/export tuned rules
-> Ansible update_rules
-> AWS WAF + OpenStack WAF
```

Các thành phần đã có:

| Thành phần | Vai trò |
| --- | --- |
| Terraform AWS/OpenStack | Tạo network, compute, security group, Route 53, Cognito, ECR |
| Ansible | Deploy VPN, gateway, WAF, app, DB, Filebeat, Logstash |
| Amazon Cognito + oauth2-proxy | Identity-aware access gateway |
| Nginx + ModSecurity + OWASP CRS | WAF runtime enforcement |
| Flask app + PostgreSQL | App demo có dữ liệu centralized |
| WireGuard | Site-to-site VPN giữa AWS và OpenStack |
| ELK | SIEM/logging dashboard |
| Feedback API | Review blocked payload và cập nhật dataset |
| ML/export script | Sinh tuned ModSecurity rule từ model |

## 5. Mapping với capstone themes

| Theme capstone | Mức độ phù hợp | Giải thích |
| --- | --- | --- |
| Đề tài 9 - SIEM trên cloud | Cao nhất | Có ELK, Filebeat, Logstash, Kibana dashboards, WAF/gateway/app/VPN logs, detect 403/WAF event |
| Đề tài 10 - ML anomaly từ logs OpenStack | Cao nhưng phải thu hẹp | Có feedback dataset và ML tuning WAF rule; nên nói là ML-assisted WAF tuning, không nhận full DL anomaly detection |
| Đề tài 1 - Zero Trust Hybrid Cloud | Trung bình | Có identity-aware gateway, auth, WAF, segmentation, VPN; chưa có SPIFFE/Istio/OPA/device posture |
| Đề tài 13 - DevSecOps CI/CD | Thấp/Trung bình | Có Terraform/Ansible và DevSecOps mapping, nhưng không tập trung CI/CD scanning; GitHub Actions cũ đã bỏ |
| Đề tài 17 - AI Cloud IDS | Trung bình thấp | Có AI/ML idea cho WAF tuning, nhưng chưa phải IDS/DL classifier đầy đủ |

Phát biểu scope nên dùng khi báo cáo:

> Trong theme SIEM/Monitoring & Incident Response, project chọn một use case cụ thể: bảo vệ ứng dụng hybrid cloud bằng Access Gateway + WAF, tập trung log về SIEM, phát hiện WAF-blocked attack, và tạo feedback loop để tune rule WAF bằng ML.

## 6. Mapping với DevSecOps phases

| Phase | Mức độ | Project mapping |
| --- | --- | --- |
| Code | Thấp | App Flask chỉ là app demo để tạo traffic, auth header và DB read/write |
| Build | Trung bình | Có Docker image app/WAF; WAF image build/push thủ công khi thay đổi base image |
| Test | Trung bình | Test SQLi 403, auth redirect, VPN, DB, failover/failback |
| Release | Trung bình | Terraform/Ansible release infra/config; rule update bằng Ansible |
| Deploy | Cao | Terraform tạo infra, Ansible deploy gateway/WAF/app/DB/VPN/logging |
| Operate | Cao | User truy cập domain thật, gateway enforce login, WAF bảo vệ app, app dùng DB qua VPN |
| Monitor | Cao | ELK dashboards theo dõi gateway, WAF, app, VPN, syslog, health |
| Logging | Cao | Filebeat/Logstash/Elasticsearch tập trung log từ nhiều node |
| Detect | Cao | WAF block SQLi/attack, SIEM hiển thị 403/top IP/path/rule |
| Response | Cao | WAF block tự động; operator label feedback; ML export rule; Ansible update WAF |
| Recover | Trung bình/Cao | Route 53 failover/failback giữa AWS và OpenStack |
| Audit/Compliance | Thấp | Có audit log feedback và SIEM log, nhưng chưa thành compliance framework |

Nếu bị hỏi "ML nằm ở phase nào?", câu trả lời nên là:

> ML nằm chủ yếu ở **Detect** và **Response**. Detect vì dùng WAF/SIEM logs và dataset feedback để phân loại hoặc tìm payload cần review. Response vì kết quả feedback/ML được export thành tuned ModSecurity rules và deploy lại WAF.

## 7. Ý chính từ feedback của thầy

Transcript từ file ghi âm bị nhiễu, nhưng có thể rút ra các ý chính sau:

- Không nên vẽ kiến trúc quá tổng quát mà không chỉ rõ đang theo dõi/log cái gì.
- Phải làm rõ "cloud" nằm ở đâu trong bài, không chỉ là phân tích ứng dụng.
- Cần tách rõ luồng người dùng, control plane và luồng logging/detection.
- Nếu nói về ML/logging thì cần chỉ ra log đến từ node nào, instance nào, ứng dụng nào.
- Không nên trình bày như đang làm toàn bộ capstone theme; nên chọn một phần có thể demo được.
- Phải chỉ ra response sau detect: WAF block, feedback, retrain/export rule, deploy lại.

Cách sửa theo feedback:

- Đổi tên project sang scope hẹp hơn: **Hybrid Cloud WAF-SIEM Feedback Loop**.
- Mở đầu slide bằng runtime security/logging/response, không mở đầu bằng full Zero Trust.
- Kiến trúc nên có 2 hình: logical flow và deployment mapping.
- Mỗi thành phần trong hình phải trả lời được: nó log gì, detect gì, response gì.

## 8. Cấu trúc slide đề xuất

| Slide | Nội dung chính |
| --- | --- |
| 1 | Title: Hybrid Cloud Runtime Security: WAF-SIEM Feedback Loop |
| 2 | Problem: logs phân tán, WAF cần tuning, hybrid cloud cần response |
| 3 | Scope: chọn một phần của theme SIEM/Monitoring, không làm full Zero Trust/DL IDS/CI-CD |
| 4 | Logical architecture: User -> DNS -> Gateway -> Auth -> WAF -> App -> DB |
| 5 | Deployment architecture: AWS/OpenStack gateway, WAF, app, VPN, DB, ELK |
| 6 | DevSecOps phase mapping: Deploy, Operate, Monitor, Logging, Detect, Response, Recover |
| 7 | Detection use case: SQLi request -> WAF 403 -> SIEM event |
| 8 | Feedback/ML response loop: review -> label -> dataset -> train/export -> deploy rule |
| 9 | Failover/recover: Route 53 primary AWS, secondary OpenStack, health check `/healthz` |
| 10 | Evaluation: auth redirect, SQLi block, SIEM ingest, Feedback API, rule update, failover |
| 11 | Limitations: TLS self-signed, DB chưa HA, ML mới ở mức WAF tuning |
| 12 | Future work: public TLS, DB replica, threat hunting playbooks, OPA/policy-as-code |

## 9. Cấu trúc báo cáo đề xuất

1. Giới thiệu và bối cảnh hybrid cloud security.
2. Vấn đề đặt ra: logging phân tán, runtime attack, WAF tuning, response loop.
3. Phạm vi đồ án và vị trí trong capstone theme.
4. Kiến trúc tổng quan.
5. Thiết kế thành phần: DNS/failover, access gateway/Cognito, WAF, app/DB, SIEM, Feedback API/ML.
6. Mapping DevSecOps phases.
7. Triển khai bằng Terraform, Ansible, ELK, Filebeat, Logstash.
8. Kịch bản kiểm thử: auth, SQLi block, SIEM ingest, feedback label, rule export/deploy, failover.
9. Kết quả và đánh giá.
10. Hạn chế.
11. Hướng phát triển.
12. Kết luận.

## 10. Nội dung cần chứng minh khi demo

| Demo | Bằng chứng cần có |
| --- | --- |
| User chưa login bị redirect | `curl -k -I https://app.nt524.io.vn/` trả 302 sang Cognito |
| Health check | `/healthz` trên AWS/OpenStack gateway trả OK |
| WAF block SQLi | SQLi payload trả HTTP 403 |
| Log vào SIEM | Kibana có event trong `siem-waf-access-*` |
| Feedback API | `/api/blocked`, `/api/feedback`, `/api/dataset/status` |
| Rule tuning | Export ra `RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf` |
| Deploy response | Ansible `waf.yml --tags update_rules` |
| Failover | Stop AWS gateway -> Route 53 trả OpenStack |
| Failback | Start AWS gateway -> Route 53 trả AWS |

## 11. Nguồn tài liệu đã dùng trong repo

- `README.md`: kiến trúc hiện tại, domain, thành phần đã hoàn thành.
- `docs/devsecops-phases.md`: mapping DevSecOps phases và Monitoring/Logging/Detect/Response.
- `docs/feedback-api.md`: Feedback API và ML/WAF tuning loop.
- `docs/task.md`: lịch sử triển khai, test failover/failback, Cognito, SIEM.
- `docs/1.md`: plan/thiet kế ban đầu cho hybrid cloud NAC/WAF/app/database.
- `docs/capstone project/Capton_projects/Projects.docx`: danh sách nhóm capstone.
- `docs/capstone project/Capton_projects/09_SIEM.md`: theme SIEM trên cloud.
- `docs/capstone project/Capton_projects/10_ML_Log_Anomaly_OpenStack.md`: theme ML từ logs.
- `docs/capstone project/Capton_projects/01_Zero_Trust_Hybrid_Cloud.md`: theme Zero Trust liên quan phụ.
- `docs/converted_markdown/audio/08.56 25-05-2026.faster-whisper-small.vi.md`: transcript audio feedback tham khảo, chất lượng nhận diện còn nhiễu.
- `docs/converted_markdown/conversion-log.tsv`: log chuyển đổi bằng MarkItDown.

## 12. Ghi chú về MarkItDown và transcript

Đã cài `markitdown[all]` từ GitHub `microsoft/markitdown` vào venv:

```text
D:\Agent\data\venv
```

Đã chuyển PDF/DOCX/ảnh/audio liên quan sang:

```text
docs/converted_markdown/
```

Lưu ý:

- PDF và DOCX chuyển được thành Markdown.
- Ảnh JPG/PNG offline cho output gần như rỗng vì không có OCR/multimodal LLM.
- File M4A gốc bị lỗi khi MarkItDown gọi audio converter do thiếu `ffprobe`; tôi đã chuyển sang WAV bằng `imageio-ffmpeg` rồi chạy MarkItDown trên WAV.
- Transcript MarkItDown mặc định nhận sai vì engine không tối ưu tiếng Việt; đã tạo thêm transcript tham khảo bằng `SpeechRecognition vi-VN` và `faster-whisper small`, nhưng cả hai vẫn nhiễu, chỉ nên dùng để rút ý chính.

