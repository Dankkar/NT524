# ĐỀ TÀI TÍCH HỢP ML VÀO HỆ THỐNG WAF GIÚP PHÁT HIỆN VÀ NGĂN NGỪA SLQ INJECTION VỚI OWASP CRS KẾT HỢP HỆ THỐNG SIEM

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

## 2. Triển khai hệ thống step-by-step

### A. Chuẩn bị hệ thống Private Cloud (Openstack)

Yêu cầu: Đã tự deploy được các core Service, tạo được Network, Instance,... Đối với trường hợp sử dụng Laptop 1 NIC để triển khai hệ thống Openstack-AIO thì Network của bạn cần trông tương tự như thế này:
┌──────────────────────────────────────────────────────────────────────────┐
│  Laptop (Ubuntu 24.04)                                                   │
│                                                                          │
│  wlp0s20f3 (WiFi DHCP) ◄── Management + Internet                         │
│       │                                                                  │
│       │  iptables MASQUERADE                                             │
│       │                                                                  │
│  br-exnat (172.10.10.1/24)   ◄── Linux Bridge, gateway cho external net  │
│       │                                                                  │
│  veth-ext ◄────────────► veth-peer                                       │
│  (in br-exnat)            (in OVS br-ex)                                 │
│                              │                                           │
│                         OVN / Neutron                                    │
│                              │                                           │
│                    Provider Network 172.10.10.0/24                       │
│                    Floating IPs: 172.10.10.200 – 172.10.10.250           │
└──────────────────────────────────────────────────────────────────────────┘

1. Tạo trước External Network (Gateway 172.10.10.1 là IP của br-exnat bridge)
```bash
openstack subnet create public-subnet \
  --network public-net \
  --subnet-range 172.10.10.0/24 \
  --gateway 172.10.10.1 \
  --allocation-pool start=172.10.10.200,end=172.10.10.250 \
  --dns-nameserver 8.8.8.8 \
  --no-dhcp
```

**Giải thích:**

- 172.10.10.0/24: Dải mạng external sử dụng qua br-exnat bridge
- gateway 172.10.10.1: IP của br-exnat = gateway cho VMs ra internet qua NAT
- allocation-pool: Dải Floating IPs cho VMs (172.10.10.200 – 250)
- Traffic đi: VM → OVN → br-ex → veth-peer → veth-ext → br-exnat → NAT → wlp0s20f3 → Internet

2. Tạo SSH key nếu chưa có:
```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/openstack_key -N ""
```
3. Tạo image Ubuntu:

```bash
# Download Ubuntu cloud image
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img -O ubuntu-24.04.img

# Upload image
openstack image create "Ubuntu-24.04" \
  --file ubuntu-24.04.img \
  --disk-format qcow2 \
  --container-format bare \
  --public
```
4. Tạo flavor:
```bash
openstack flavor create m1.small \
  --ram 2048 \
  --disk 10 \
  --vcpus 1
```


### B. Chuẩn bị hệ thống Public Cloud (AWS)

1. Đã cấu hình AWS CLI tại local, nếu chưa thì xem tại:[Installing or updating to the latest version of the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

2. Chọn Region muốn triển khai ví dụ: ap-southeast-1 (Singapore)

3. Chọn 1 VPC hoặc tạo mới. Lấy:
    * ID VPC
    * ID Subnet
    * ID Route tables
    * ID Network Connections

### C. Tiến hành triển khai và cấu hình

#### Terraform

1. **Openstack**:

```bash
# Tìm External Network ID:
source ~/kolla-venv/bin/activate
source /etc/kolla/admin-openrc.sh
openstack network list --external

E.g:
(kolla-venv) nhatnguyen@openstack-aio:/etc/kolla/ansible/inventory$ openstack network list --external
+--------------------------------------+------------+--------------------------------------+
| ID                                   | Name       | Subnets                              |
+--------------------------------------+------------+--------------------------------------+
| fe5863fe-28c1-4232-ae66-bfe39ceff5c9 | public-net | 7073f15f-66aa-4328-a3d5-eab1a7c33148 |
+--------------------------------------+------------+--------------------------------------+

=> Lấy ID: fe5863fe-28c1-4232-ae66-bfe39ceff5c9 và dán vào <OPENSTACK_EXTERNAL_NETWORK_ID> tại external_network_id của terraform/openstack/terraform.tfvars

# Kiểm tra và triển khai hạ tầng
cd terraform/openstack
terraform init
terraform plan
terraform apply
terraform output

=> Ghi lại vpn_public_ip và app_node_ip
E.g:
Outputs:
app_node_ip = "10.0.1.65"
vpn_public_ip = "172.10.10.240"
```

2. **AWS**:
```bash
# Kiểm tra IP public (IP mà Internet đang nhìn thấy Laptop của bạn đi ra ngoài)
curl -fsS https://checkip.amazonaws.com
=> Đây là biến openstack_vpn_public_cidr cho lệnh tiếp theo

# Chỉ định hoặc tạo mới SSH Key cho AWS
ssh-keygen -t rsa -b 4096 -f ~/.ssh/aws_vpn_key -N ""

# Chỉnh sửa AWS variables
cd terraform/aws
cp terraform.tfvars.example terraform.tfvars

=> Sửa terraform.tfvars: vpc_id, subnet_id, route_table_id, openstack_vpn_public_cidr, public_key_path

# Kiểm tra và triển khai hạ tầng
cd terraform/aws
terraform init
terraform plan
terraform apply
terraform output

=> Ghi lại output
Outputs:
ecr_repository_url = "<AWS-ACCOUNT-ID>.dkr.ecr.ap-southeast-1.amazonaws.com/my-waf-nginx"
github_actions_role_arn = "arn:aws:iam::<AWS-ACCOUNT-ID>:role/github-actions-ecr-push-role"
vpn_instance_id = "i-0a0bfe0527c2eb5f5"
vpn_network_interface_id = "eni-057d589794009d1f4"
vpn_private_ip = "172.31.42.199"
vpn_public_ip = "18.139.214.17"
waf_private_ip = "172.31.40.41"
waf_public_ip = "47.131.193.254"
```
#### ELK Local
```bash
cd elk
sudo sysctl -w vm.max_map_count=262144
sudo docker compose up -d --remove-orphans
```
### Build/push WAF image lên ECR trước khi chạy Ansible
```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM

# kiểm tra ECR repo có tồn tại chưa
aws ecr describe-repositories --region ap-southeast-1 --repository-names my-waf-nginx

# Build/push WAF image lên ECR trước khi chạy Ansible
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin <AWS-ACCOUNT-ID>.dkr.ecr.ap-southeast-1.amazonaws.com

docker build --network=host \
  -t <AWS-ACCOUNT-ID>.dkr.ecr.ap-southeast-1.amazonaws.com/my-waf-nginx:latest \
  -f ansible/roles/nginx_waf/files/Dockerfile \
  ansible/roles/nginx_waf/files/

docker push <AWS-ACCOUNT-ID>.dkr.ecr.ap-southeast-1.amazonaws.com/my-waf-nginx:latest
```

#### Ansible
```bash
# Điền các IP cần thiết vào file hosts.yml
cd ansible/inventories/production
cp hosts.example.yml hosts.yml
* aws-vpn.ansible_host = AWS vpn_public_ip
* aws-waf.ansible_host = AWS waf_public_ip
* openstack-vpn.ansible_host = OpenStack vpn_public_ip
* openstack-app.ansible_host = OpenStack app_node_ip
* ProxyCommand của openstack-app dùng OpenStack vpn_public_ip

cp all.example.yml all.yml
* app_backend_host = OpenStack app_node_ip
* CHANGE_ME_AWS_ACCOUNT_ID = AWS Account ID

# Chạy Ansible
source /home/nhatnguyen/kolla-venv/bin/activate
source /etc/kolla/admin-openrc.sh 
cd ansible
ansible all -m ping
ansible-playbook site.yml
```
---

## 3. Kiểm tra hệ thống sau khi deploy
### ELK
1. Provision Kibana
```bash
cd elk
python3 kibana/provision_kibana.py
```
---

## 4. Chi tiết về cấu trúc
### A. Tự động hóa Hạ tầng AWS (OIDC & ECR)
**Chi tiết file:** terraform/aws/oidc.tf
*   **AWS OIDC Provider:** Tích hợp OIDC liên kết an toàn giữa AWS và GitHub Actions.
*   **IAM Role (`github-actions-ecr-push-role`):** Cấp quyền cho GitHub Actions tự động đăng nhập và đẩy ảnh lên ECR thông qua Role ARN mà không cần dùng Access Keys.
*   **IAM Instance Profile (`waf-ec2-instance-profile`):** Gắn trực tiếp vào máy ảo AWS WAF EC2, cấp quyền cho máy ảo tự đăng nhập và kéo ảnh từ ECR (`ECR ReadOnly`) mà không cần lưu bất cứ thông tin bảo mật nào trên ổ đĩa.
*   **ECR Repository (`my-waf-nginx`):** Kho chứa Docker Image WAF chính thức tích hợp quét lỗ hổng khi push (`scan_on_push = true`).

### B. Cài đặt Nginx WAF bằng Docker Container
**Chi tiết file:** 
*   ansible/roles/nginx_waf/tasks/main.yml
*   ansible/roles/nginx_waf/templates/docker-compose.yml.j2
*   ansible/roles/nginx_waf/handlers/main.yml

*   **Dọn dẹp Nginx cũ:** Gỡ bỏ hoàn toàn Nginx cài native trên hệ điều hành của AWS Host để giải phóng cổng 80/443.
*   **Cài đặt Docker CE & Docker Compose:** Ansible tự động cài đặt Docker lên AWS Host.
*   **Chạy WAF Container dạng Host Network:** Docker Compose kích hoạt container WAF sử dụng card mạng Host để kết nối trực tiếp với WireGuard sang OpenStack.
*   **Mount Volume Rules:** File rule set từ ML `RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf` được mount trực tiếp từ Host vào Container.
*   **Cơ chế Hot-Reload (Không Downtime):** Khi rule thay đổi, Ansible chỉ chạy lệnh `docker exec waf-nginx nginx -s reload`. Rule mới áp dụng sau **0.5 giây** mà không cần khởi động lại container, không gây gián đoạn người dùng.

### C. Pipeline CI/CD GitHub Actions (Chống Vòng Lặp Vô Hạn)
**Chi tiết file:** .github/workflows/deploy.yml

Pipeline tự động chạy khi push code lên GitHub nhưng **hoàn toàn loại trừ vòng lặp vô hạn**:
*   **Cơ chế paths-ignore:**
    ```yaml
    paths-ignore:
      - 'ansible/roles/nginx_waf/files/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf'
      - 'modsec-learn/**'
      - '**.md'
    ```
    *Khi quy trình retraining ML xuất ra file Rule mới và commit ngược lại Git, GitHub Actions đọc thấy tệp tin này nằm trong danh sách ignore và **KHÔNG** kích hoạt lại build image, ngăn ngừa vòng lặp vô hạn.*
*   **SAST & Trivy Scan:** Quét mã nguồn tĩnh và quét lỗ hổng thư viện bên trong Docker Image trước khi đẩy lên ECR.
*   **SSH Deploy:** SSH trực tiếp vào EC2, sử dụng IAM Instance Profile của EC2 để đăng nhập ECR và chạy `docker compose pull && docker compose up -d` tức thì.

---

## 5. Hướng dẫn vận hành hệ thống

### Bước 1: Thiết lập Secrets trên GitHub
Để GitHub Actions có quyền kết nối tới AWS và EC2 ta cấu hình các Secrets sau tại Repo GitHub (*Settings -> Secrets and variables -> Actions -> Repository secrets*):
1.  **`AWS_ROLE_ARN`**: `arn:aws:iam::<AWS-ACCOUNT-ID>:role/github-actions-ecr-push-role`
2.  **`EC2_WAF_HOST`**: `<waf_public_ip>' (IP Public của AWS WAF Node)
3.  **`EC2_SSH_PRIVATE_KEY`**: Nội dung tệp Private SSH Key dùng để đăng nhập vào WAF Node.

### Bước 2: Kích hoạt Triển khai lần đầu (Git Push)
Sau khi chỉnh sửa xong mã nguồn. Push lên GitHub để kích hoạt build WAF Image đầu tiên:
```bash
git add .
git commit -m "DevSecOps: Set up Dockerized WAF with GitHub Actions CI/CD"
git push origin main
```
*Vào tab **Actions** trên GitHub để theo dõi quy trình build, quét Trivy và Deploy tự động.*

### Bước 3: Chu trình Retrain Mô hình & Cập nhật luật ML (Zero Downtime)
Yêu cầu, phải hoàn tất các bước trong SIEM/Local_ML.md trước đó.Khi thực hiện huấn luyện lại mô hình ML thành công ở máy local:
1.  Chạy script trích xuất luật tối ưu từ mô hình của bạn:
    ```bash
    cp -r ~/modsec-learn .
    cp scripts/*.py modsec-learn/scripts/
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
---

## 6. Thiết lập Cảnh báo (Alerting) & Phản hồi SOC (Feedback Loop)

Hệ thống cung cấp chu trình khép kín giúp SOC analyst có thể phát hiện cảnh báo và trực tiếp gắn nhãn dữ liệu (đúng/sai) ngay từ Kibana hoặc qua Dashboard tương tác để tái huấn luyện mô hình.

### A. Khởi chạy và Sử dụng SOC Feedback Dashboard (Port 5005)
Chạy dịch vụ feedback API và giao diện Dashboard ở máy huấn luyện local:
```bash
python3 modsec-learn/scripts/feedback_api.py
```
Giao diện quản lý sự cố tương tác sẽ khả dụng tại **`http://localhost:5005/`**.
*   **Tính năng chính:**
    1.  **Ghi nhận mã sự cố:** Hiển thị trực tiếp mã định danh sự cố `ES Doc ID` lấy từ Elasticsearch.
    2.  **Lưu giữ trạng thái:** Đọc dữ liệu local tại thời điểm tải trang. Nếu một payload đã được duyệt và lưu vào dataset, giao diện sẽ hiển thị trạng thái tĩnh **Confirmed Attack 🔴** hoặc **Reclassified Benign 🟢** thay vì hiển thị lại các nút bấm.
    3.  **Hành động một chạm:** Analyst có thể phân loại nhanh các sự cố chưa xử lý bằng cách nhấn nút gắn nhãn.

### B. Thiết lập Cảnh báo nội bộ (Alerting Rules) trên Kibana
Nếu không cấu hình các dịch vụ Webhook ngoài (Slack/Discord), bạn nên ghi nhận cảnh báo vào một Elasticsearch Index riêng biệt:
1.  Truy cập Kibana Dashboard, vào **Stack Management** -> **Rules** -> click **Create rule**.
2.  Chọn loại rule **Elasticsearch query** -> Chọn **Query DSL**
3.  Cấu hình Index Pattern / Data View là `siem-hybrid-*`.
4.  Cấu hình trường thời gian (Time field) là **`@timestamp`**.
5.  Định nghĩa bộ lọc (Query DSL):
```json
{
    "query": {
        "bool": {
            "must": [
                {
                    "term": {
                        "fields.node_role.keyword": "waf"
                    }
                },
                {
                    "query_string": {
                        "query": "message: *403*"
                    }
                }
            ]
        }
    }
}
 ```
6.  Chọn điều kiện: `WHEN count() OVER all documents IS ABOVE 10 FOR THE LAST 5 minutes`.
7.  Trong mục **Actions**, chọn Connector là **Index** (Ghi vào index nội bộ):
    *   **Index:** `siem-alerts-history`
    *   **Document (JSON):**
```json
{
    "alert_time": "{{context.date}}",
    "rule_name": "{{rule.name}}",
    "rule_id": "{{rule.id}}",
    "message": "Phát hiện tấn công dồn dập bị chặn bởi WAF Node!",
    "matched_requests_count": "{{context.hits.total.value}}"
}
```

### C. Thiết lập Dashboard Giám sát trên Kibana Lens
#### 1. Trích xuất địa chỉ IP người dùng (Runtime Field)
Vì IP client nằm bên trong log `message` thô, hãy tạo trường ảo `waf_client_ip`:
1.  Vào **Stack Management** -> **Data Views** -> Chọn `siem-hybrid-*`.
2.  Click **Create field** ở góc phải trên:
    *   **Name:** `waf_client_ip`
    *   **Type:** `Keyword`
    *   **Painless script:**
```bash
String msg = params['_source']['message'];

if (msg != null) {
  int marker = msg.indexOf("HTTP/1.1");

  if (marker != -1) {
    int quoteEnd = msg.indexOf("\\\"", marker);

    if (quoteEnd != -1) {
      int statusStart = quoteEnd + 3;
      int statusEnd = msg.indexOf(" ", statusStart);

      if (statusEnd != -1) {
        emit(msg.substring(statusStart, statusEnd));
        return;
      }
    }
  }
}

emit("unknown");
```
*   **Name:** `waf_status`
*   **Type:** `Keyword`
*   **Painless script:**
```bash
String msg = params['_source']['message'];

if (msg != null) {
  int marker = msg.indexOf("HTTP/1.1");

  if (marker != -1) {
    int quoteEnd = msg.indexOf("\\\"", marker);

    if (quoteEnd != -1) {
      int statusStart = quoteEnd + 3;
      int statusEnd = msg.indexOf(" ", statusStart);

      if (statusEnd != -1) {
        emit(msg.substring(statusStart, statusEnd));
        return;
      }
    }
  }
}

emit("unknown");
```

#### 2. Xây dựng trang giám sát bảo mật & sức khỏe hệ thống
Vào **Analytics** -> **Dashboard** -> click **Create dashboard** và thêm các Widget sau:
*   **Tổng số cuộc tấn công bị chặn (Metric):**
    *   Filter: `fields.node_role : "waf" and waf_status : "403"`
    *   Primary metric: `Count of records`
*   **Top IP Tấn công (Data Table):**
    *   Filter: `fields.node_role : "waf" and waf_status : "403"`
    *   Rows: Kéo thả trường `waf_client_ip`
    *   Metric: `Count of records`
*   **Tần suất chặn theo thời gian (Line/Area Chart):**
    *   Filter: `fields.node_role : "waf" and waf_status : "403"`
    *   X-axis: `@timestamp` | Y-axis: `Count of records` | Breakdown: `waf_client_ip`
*   **Tỉ lệ mã trạng thái HTTP tại WAF Proxy (Donut Chart):**
    *   Filter: `fields.node_role : "waf"`
    *   Metric: `Count of records` | Slice by: `waf_status`
*   **Kiểm toán đăng nhập SSH (Data Table):**
    *   Filter: `message.keyword : *Accepted\ publickey* or message.keyword : *Accepted\ password*`
    *   Rows: `@timestamp`, `host.name.keyword`, `message.keyword`

---

## 7. Tái huấn luyện Mô hình học máy (Retraining Pipeline)

Sau khi thu thập đủ dữ liệu feedback và phân tách các log từ máy chủ (tránh trùng lặp nhờ cơ chế giải quyết xung đột tích hợp sẵn trong script `extract_logs.py`), bạn tiến hành tái huấn luyện mô hình theo các bước sau:

1.  **Trích xuất log mới và đồng bộ dataset:**
    ```bash
    python3 modsec-learn/scripts/extract_logs.py
    ```
2.  **Kích hoạt môi trường ảo AI:**
    ```bash
    source ~/modsec-ai-venv/bin/activate
    ```
3.  **Vào thư mục dự án và chạy huấn luyện:**
    ```bash
    cd ~/modsec-learn
    python3 scripts/run_training.py
    ```
    *Script sẽ nạp tập dữ liệu huấn luyện đã làm sạch, trích xuất đặc trưng cho các Paranoia Levels từ 1 đến 4, huấn luyện các mô hình SVM, Random Forest, Logistic Regression và xuất các tệp `.joblib` mới vào `data/models/`.*
4.  **Kiểm tra và đánh giá mô hình:**
    ```bash
    python3 scripts/run_experiments.py
    ```
5.  **Trích xuất luật loại trừ tối ưu từ mô hình AI:**
    ```bash
    python3 scripts/export_tuned_rules.py --model linear_svc_pl4_l1.joblib
    ```
    *Script sẽ phân tích trọng số mô hình SVM L1, tạo tệp `RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf` chứa các ID bị loại bỏ (trọng số 0) và ghi trực tiếp vào thư mục files của Ansible.*
6.  **Đồng bộ và kích hoạt luật mới lên WAF Node (AWS):**
    ```bash
    cd ../ansible
    ansible-playbook -i inventories/production/hosts.yml waf.yml
    ```
    *Ansible tự động sao chép tệp luật loại trừ mới lên máy chủ AWS và ra lệnh nạp lại cấu hình Nginx (`nginx -s reload`) giúp luật có hiệu lực ngay lập tức với zero-downtime.*

---

## 9. Thư mục Scripts MLOps dự phòng cho GitHub

Để phục vụ lưu trữ phiên bản trên GitHub (do thư mục `modsec-learn` không thể đẩy trực tiếp lên Git của repo chính), toàn bộ 7 script MLOps và sinh dữ liệu tùy chỉnh trong phiên làm việc đã được sao chép ra thư mục:
📁 **`scripts/`** (nằm trực tiếp tại gốc của Repo chính).

Các script bao gồm:
*   `generate_benign.py`: Giả lập lưu lượng sạch từ người dùng bình thường vào ứng dụng Juice Shop.
*   `generate_attacks.py`: Giả lập lưu lượng tấn công SQL Injection bị WAF chặn để lấy mẫu log 403.
*   `feedback_api.py`: Giao diện Dashboard quản lý sự cố và tiếp nhận nhãn phản hồi SOC tự động lưu trạng thái.
*   `extract_logs.py`: Quét log từ SIEM về máy huấn luyện, tự động loại bỏ trùng lặp và xung đột dữ liệu.
*   `run_training.py`: Huấn luyện lại toàn bộ mô hình AI cho cả 4 Paranoia Levels.
*   `run_experiments.py`: Đo lường, chạy kiểm thử đánh giá độ chính xác của các mô hình.
*   `export_tuned_rules.py`: Trích xuất các rule dư thừa từ mô hình tối ưu hóa SVM L1 và lưu trực tiếp vào thư mục phân phối của Ansible.

## 10. Dọn dẹp môi trường (Destroy)

1. **Hủy tài nguyên trên OpenStack**:
   ```bash
   source ~/kolla-venv/bin/activate
   source /etc/kolla/admin-openrc.sh
   cd /home/deployer/Downloads/Project/terraform/openstack
   terraform destroy -auto-approve
   ```

2. **Hủy tài nguyên trên AWS**:
   ```bash
   cd /home/deployer/Downloads/Project/terraform/aws
   terraform destroy -auto-approve
   ```

3. **Dọn dẹp cụm Elasticsearch/Kibana local**:
   ```bash
   cd /home/deployer/Downloads/Project/elk
   sudo docker compose down -v
    ```

*(Tùy chọn) Dọn dẹp SSH known_hosts để lần sau không bị lỗi cảnh báo Man-in-the-middle do IP cũ cấp lại cho máy ảo mới:*
```bash
rm -f ~/.ssh/known_hosts