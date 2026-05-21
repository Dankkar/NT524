# Hướng Dẫn Rebuild & Deploy Toàn Bộ Hệ Thống Từ Đầu (Sau khi `terraform destroy`)

Tài liệu này mô tả chi tiết thứ tự chạy các lệnh từ đầu hoặc sau khi hủy toàn bộ hạ tầng để dựng lại hệ thống SIEM Hybrid Cloud.

---

## BƯỚC 1: Dọn dẹp môi trường cũ (Destroy)

Nếu bạn cần dọn dẹp hệ thống cũ, hãy chạy các lệnh sau:

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

---

## BƯỚC 2: Triển khai hạ tầng bằng Terraform (Deploy)

1. **Triển khai OpenStack App & VPN Nodes**:
   ```bash
   source ~/kolla-venv/bin/activate
   source /etc/kolla/admin-openrc.sh
   cd /home/deployer/Downloads/Project/terraform/openstack
   terraform init
   terraform apply -auto-approve
   ```
   *Ghi lại các IP từ output:*
   - `app_node_ip` (Ví dụ: `10.0.1.185`)
   - `vpn_public_ip` (Ví dụ: `172.10.10.232`)

2. **Triển khai AWS WAF & VPN Nodes**:
   - Trước tiên, kiểm tra IP public thật của router/NAT tại local laptop (do IP nhà mạng có thể thay đổi):
     ```bash
     curl -fsS https://checkip.amazonaws.com
     ```
   - Mở file `/home/deployer/Downloads/Project/terraform/aws/terraform.tfvars` và cập nhật giá trị của `openstack_vpn_public_cidr` với IP public trên (dưới dạng `<IP>/32`).
   - Chạy lệnh triển khai:
     ```bash
     cd /home/deployer/Downloads/Project/terraform/aws
     terraform init
     terraform apply -auto-approve
     ```
   *Ghi lại các IP từ output:*
   - `vpn_public_ip` (Ví dụ: `18.136.65.78`)
   - `waf_public_ip` (Ví dụ: `54.254.229.116`)

---

## BƯỚC 3: Cập nhật Cấu hình Ansible

1. **Cập nhật Inventory Hosts**:
   Mở file `/home/deployer/Downloads/Project/ansible/inventories/production/hosts.yml` và thay thế các IP mới tương ứng:
   - `aws-vpn` -> `ansible_host`: Điền `vpn_public_ip` của AWS.
   - `aws-waf` -> `ansible_host`: Điền `waf_public_ip` của AWS.
   - `openstack-vpn` -> `ansible_host`: Điền `vpn_public_ip` (floating IP) của OpenStack.
   - `openstack-app` -> `ProxyCommand`: Cập nhật IP của OpenStack VPN Node ở phần jump target (`ubuntu@<OPENSTACK_VPN_FIP>`).

2. **Cập nhật Variables**:
   Mở file `/home/deployer/Downloads/Project/ansible/inventories/production/group_vars/all.yml`:
   - `app_backend_host`: Cập nhật IP private của OpenStack App Node (`app_node_ip` ở Bước 2.1).

3. **Kiểm tra kết nối Ansible**:
   ```bash
   source ~/kolla-venv/bin/activate
   cd /home/deployer/Downloads/Project/ansible
   ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
   ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
   ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
   ansible -i inventories/production/hosts.yml all -m ping
   ```
   *(Mong đợi tất cả 4 host trả về `ping: pong`).*

---

## BƯỚC 4: Build & Push Docker Image WAF lên AWS ECR

Do WAF EC2 Node kéo trực tiếp Docker image từ kho chứa ECR của bạn, bạn cần build và push ảnh Docker WAF lên ECR:

1. **Đăng nhập AWS ECR**:
   ```bash
   aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin 211116632423.dkr.ecr.ap-southeast-1.amazonaws.com
   ```

2. **Build Docker Image** (sử dụng network host để tránh xung đột bridge):
   ```bash
   cd /home/deployer/Downloads/Project
   docker build --network=host -t 211116632423.dkr.ecr.ap-southeast-1.amazonaws.com/my-waf-nginx:latest -f ansible/roles/nginx_waf/files/Dockerfile ansible/roles/nginx_waf/files/
   ```

3. **Push Docker Image**:
   ```bash
   docker push 211116632423.dkr.ecr.ap-southeast-1.amazonaws.com/my-waf-nginx:latest
   ```

---

## BƯỚC 5: Khởi động Cụm SIEM Local (Elasticsearch & Kibana)

Cấu hình bộ nhớ ảo và khởi động container SIEM trên máy local:
```bash
cd /home/deployer/Downloads/Project/elk
sudo sysctl -w vm.max_map_count=262144
sudo docker compose up -d --remove-orphans
```

---

## BƯỚC 6: Triển khai Toàn Bộ Dịch Vụ bằng Ansible Playbook

Sử dụng playbook tổng `site.yml` để tự động hóa toàn bộ việc cấu hình VPN, Logstash, App Node và WAF Node theo đúng thứ tự:
```bash
source ~/kolla-venv/bin/activate
cd /home/deployer/Downloads/Project/ansible
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible-playbook site.yml
```

---

## BƯỚC 7: Xác Minh Hoạt Động Hệ Thống

1. **Kiểm tra Reverse Proxy & Kết nối qua VPN**:
   ```bash
   curl -sI http://<AWS_WAF_PUBLIC_IP>
   ```
   *(Mong đợi trả về `HTTP/1.1 200 OK` đi kèm header `X-Recruiting: /#/jobs` của Juice Shop).*

2. **Kiểm tra ModSecurity WAF**:
   ```bash
   curl -i "http://<AWS_WAF_PUBLIC_IP>/?id='foo'%20or%201=1"
   ```
   *(Mong đợi trả về `HTTP/1.1 403 Forbidden` thể hiện ModSecurity đã chặn thành công).*

3. **Kiểm tra Log Nhận Được trong Elasticsearch**:
   ```bash
   curl -s -X GET "http://172.10.10.1:9200/siem-hybrid-*/_search?pretty" -H 'Content-Type: application/json' -d'
   {
     "size": 0,
     "aggs": {
       "node_roles": {
         "terms": {
           "field": "fields.node_role.keyword"
         }
       }
     }
   }'
   ```
   *(Mong đợi trả về danh sách phân bổ log gồm cả hai node `app` và `waf`).*
