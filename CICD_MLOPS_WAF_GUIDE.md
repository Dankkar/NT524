# HƯỚNG DẪN CHI TIẾT HỆ THỐNG DEVSECOPS & MLOPS WAF MODSECURITY

Tài liệu này mô tả chi tiết các thay đổi cấu trúc, kiến trúc triển khai Container hóa và quy trình CI/CD tự động hóa bảo mật thông qua GitHub Actions kết hợp Ansible cho hệ thống ModSecurity WAF của bạn.

---

## 1. Kiến Trúc Tổng Quan Hệ Thống

Hệ thống hoạt động theo mô hình **Hybrid Cloud Security**:
*   **AWS WAF Node:** Hoạt động như một Reverse Proxy tiếp nhận Traffic công cộng, tích hợp bộ nhân ModSecurity v3 và CRS v4 để lọc các Request độc hại.
*   **WireGuard VPN Tunnel:** Kênh truyền mã hóa nối liền dải mạng AWS VPC (`172.31.0.0/16`) và OpenStack Private Subnet (`10.0.1.0/24`).
*   **OpenStack App Node (`10.0.1.220`):** Máy chủ ứng dụng thực tế chạy Juice Shop được bảo vệ hoàn toàn phía sau WAF.

```
[Người dùng] 
     │  (Traffic công cộng)
     ▼
[AWS WAF Node (Container Nginx + ModSecurity)]
     │
     ▼  (VPN Tunnel - WireGuard)
[OpenStack App Node (Juice Shop: 10.0.1.220)]
```

---

## 2. Chi Tiết Các Thay Đổi Cấu Trúc

### A. Tự động hóa Hạ tầng AWS (OIDC & ECR)
👉 **Chi tiết file:** [terraform/aws/oidc.tf](file:///home/deployer/Downloads/Project/terraform/aws/oidc.tf)
*   **AWS OIDC Provider:** Tích hợp OIDC liên kết an toàn giữa AWS và GitHub Actions.
*   **IAM Role (`github-actions-ecr-push-role`):** Cấp quyền cho GitHub Actions tự động đăng nhập và đẩy ảnh lên ECR thông qua Role ARN mà không cần dùng Access Keys.
*   **IAM Instance Profile (`waf-ec2-instance-profile`):** Gắn trực tiếp vào máy ảo AWS WAF EC2, cấp quyền cho máy ảo tự đăng nhập và kéo ảnh từ ECR (`ECR ReadOnly`) mà không cần lưu bất cứ thông tin bảo mật nào trên ổ đĩa.
*   **ECR Repository (`my-waf-nginx`):** Kho chứa Docker Image WAF chính thức tích hợp quét lỗ hổng khi push (`scan_on_push = true`).

---

### B. Chuyển đổi Nginx WAF sang Docker Container
👉 **Chi tiết file:** 
*   [ansible/roles/nginx_waf/tasks/main.yml](file:///home/deployer/Downloads/Project/ansible/roles/nginx_waf/tasks/main.yml)
*   [ansible/roles/nginx_waf/templates/docker-compose.yml.j2](file:///home/deployer/Downloads/Project/ansible/roles/nginx_waf/templates/docker-compose.yml.j2)
*   [ansible/roles/nginx_waf/handlers/main.yml](file:///home/deployer/Downloads/Project/ansible/roles/nginx_waf/handlers/main.yml)

*   **Dọn dẹp Nginx cũ:** Gỡ bỏ hoàn toàn Nginx cài native trên hệ điều hành của AWS Host để giải phóng cổng 80/443.
*   **Cài đặt Docker CE & Docker Compose:** Ansible tự động cài đặt Docker lên AWS Host.
*   **Chạy WAF Container dạng Host Network:** Docker Compose kích hoạt container WAF sử dụng card mạng Host để kết nối trực tiếp với WireGuard sang OpenStack.
*   **Mount Volume Rules:** File luật loại trừ ML `RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf` được mount trực tiếp từ Host vào Container.
*   **Cơ chế Hot-Reload (Không Downtime):** Khi tệp luật thay đổi, Ansible chỉ chạy lệnh `docker exec waf-nginx nginx -s reload`. Luật mới áp dụng sau **0.5 giây** mà không cần khởi động lại container, không gây gián đoạn người dùng.

---

### C. Pipeline CI/CD GitHub Actions (Chống Vòng Lặp Vô Hạn)
👉 **Chi tiết file:** [.github/workflows/deploy.yml](file:///home/deployer/Downloads/Project/.github/workflows/deploy.yml)

Pipeline tự động chạy khi bạn push code lên GitHub nhưng **hoàn toàn loại trừ vòng lặp vô hạn**:
*   **Cơ chế paths-ignore:**
    ```yaml
    paths-ignore:
      - 'ansible/roles/nginx_waf/files/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf'
      - 'modsec-learn/**'
      - '**.md'
    ```
    *Khi quy trình retraining ML của bạn xuất ra file luật mới và commit ngược lại Git, GitHub Actions đọc thấy tệp tin này nằm trong danh sách ignore và **KHÔNG** kích hoạt lại build image, ngăn ngừa tuyệt đối vòng lặp vô hạn.*
*   **SAST & Trivy Scan:** Quét mã nguồn tĩnh và quét lỗ hổng thư viện bên trong Docker Image trước khi đẩy lên ECR.
*   **SSH Deploy:** SSH trực tiếp vào EC2, sử dụng IAM Instance Profile của EC2 để đăng nhập ECR và chạy `docker compose pull && docker compose up -d` tức thì.

---

## 3. Hướng Dẫn Vận Hành Hệ Thống

### Bước 1: Thiết lập Secrets trên GitHub
Để GitHub Actions có quyền kết nối tới AWS và EC2, bạn cần cấu hình các Secrets sau tại Repo GitHub (*Settings -> Secrets and variables -> Actions -> Repository secrets*):

1.  **`AWS_ROLE_ARN`**: `arn:aws:iam::211116632423:role/github-actions-ecr-push-role`
2.  **`EC2_WAF_HOST`**: `47.131.144.87` (IP Public của AWS WAF Node)
3.  **`EC2_SSH_PRIVATE_KEY`**: Nội dung tệp Private SSH Key dùng để đăng nhập vào WAF Node.

---

### Bước 2: Kích hoạt Triển khai lần đầu (Git Push)
Sau khi chỉnh sửa xong mã nguồn, bạn thực hiện push lên GitHub để kích hoạt build WAF Image đầu tiên:
```bash
git add .
git commit -m "DevSecOps: Set up Dockerized WAF with GitHub Actions CI/CD"
git push origin main
```
*Bạn có thể vào tab **Actions** trên GitHub để theo dõi quy trình build, quét Trivy và Deploy tự động.*

---

### Bước 3: Chu trình Retrain Mô hình & Cập nhật luật ML (Zero Downtime)
Khi bạn thực hiện huấn luyện lại mô hình ML thành công ở máy local:
1.  Chạy script trích xuất luật tối ưu từ mô hình của bạn:
    ```bash
    python3 modsec-learn/scripts/export_tuned_rules.py
    ```
    *Script này sẽ tự động ghi đè tệp luật loại trừ mới vào thư mục local:* `ansible/roles/nginx_waf/files/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf`.
2.  Chạy playbook Ansible để đẩy luật mới lên WAF cực nhanh (chỉ mất 2 giây):
    ```bash
    ansible-playbook -i inventories/production/hosts.yml waf.yml --tags "update_rules"
    ```
    *Ansible sẽ đồng bộ tệp luật lên AWS Host và gọi lệnh reload Nginx container. Luật áp dụng ngay lập tức mà không gây downtime!*
3.  Đẩy tệp luật mới lên Git để lưu trữ lịch sử phiên bản (GitOps):
    ```bash
    git add ansible/roles/nginx_waf/files/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf
    git commit -m "MLOps: Tuned rules update from MLflow run [skip ci]"
    git push origin main
    ```
    *(GitHub Actions sẽ tự động bỏ qua không chạy lại build nhờ cấu hình `paths-ignore` và tag `[skip ci]`).*

---

### Bước 4: Kiểm tra trạng thái hoạt động trên AWS WAF Node
Đăng nhập SSH vào máy chủ AWS WAF Node và chạy các lệnh kiểm tra:

*   **Xem tài nguyên tiêu hao thực tế (Live Stats):**
    ```bash
    docker stats waf-nginx
    ```
*   **Xem lịch sử Log truy cập của WAF:**
    ```bash
    docker logs -f waf-nginx
    ```
*   **Kiểm tra xem ModSecurity đã được nạp thành công chưa:**
    ```bash
    docker exec waf-nginx nginx -T | grep -i modsecurity
    ```
