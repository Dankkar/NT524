# Hướng dẫn sử dụng Terraform cho AWS (Refactored)

Tài liệu này hướng dẫn cách cấu hình và triển khai hạ tầng WAF & VPN Gateway trên AWS dùng để kết nối với OpenStack tạo thành hệ thống SIEM Hybrid Cloud.

## Cập nhật hiện tại

- Terraform dùng biến `aws_profile`; để rỗng thì dùng AWS credential chain mặc định của máy chạy.
- Hạ tầng AWS chính đã tồn tại và được quản lý qua state hiện tại, không tạo lại VPC/EC2 nếu state khớp.
- OpenStack secondary gateway hiện tại là `172.10.10.209`.
- WAN IP hiện tại của OpenStack AIO là `14.191.231.153/32`; security group AWS VPN đã cho phép UDP `51820` từ CIDR này.
- Route 53 record `app.nt524.io.vn` secondary failover đã trỏ tới `172.10.10.209`.
- Terraform đã được chuẩn bị để tạo thêm EC2 `aws-db` riêng làm PostgreSQL primary.
- Terraform remote state đã được chuẩn bị:
  - S3 bucket: `nt524-terraform-state-211116632423-ap-southeast-1`
  - DynamoDB lock table: `nt524-terraform-locks`

Sau khi clone repo, để dùng state chung:

```bash
terraform -chdir=terraform/aws init -backend-config=../backend.aws.hcl.example
terraform -chdir=terraform/openstack init -backend-config=../backend.openstack.hcl.example
```

---

## 1. Cấu trúc thư mục hạ tầng AWS

Hạ tầng AWS cũng được chia làm các module con để đảm bảo tính cô đọng và dễ bảo trì:
*   **[main.tf](file:///home/deployer/Downloads/Project/terraform/aws/main.tf)**: File chính gọi module `network`, `security_group`, `compute` và thiết lập route.
*   **[provider.tf](file:///home/deployer/Downloads/Project/terraform/aws/provider.tf)**: Cấu hình AWS provider và AWS region.
*   **[variables.tf](file:///home/deployer/Downloads/Project/terraform/aws/variables.tf)**: Khai báo các tham số đầu vào.
*   **[terraform.tfvars.example](file:///home/deployer/Downloads/Project/terraform/aws/terraform.tfvars.example)**: File mẫu hướng dẫn điền tham số.
*   **[terraform.tfvars](file:///home/deployer/Downloads/Project/terraform/aws/terraform.tfvars)**: **[NƠI CHỈNH SỬA CHÍNH]** File chứa cấu hình thực tế cho AWS Account của bạn (file này đã được đưa vào `.gitignore` để bảo mật thông tin tài khoản).

---

## 2. Các tham số cần cấu hình trong `terraform.tfvars`

Hãy nhân bản file `terraform.tfvars.example` thành `terraform.tfvars` và cấu hình các giá trị thực tế sau:

```bash
cd /home/deployer/Downloads/Project/terraform/aws
cp terraform.tfvars.example terraform.tfvars
```

### 2.1. Cấu hình Tài khoản AWS & Môi trường sẵn có
*   `aws_region`: Vùng AWS bạn muốn khởi tạo (mặc định: `"ap-southeast-1"`).
*   `vpc_id`: **Bắt buộc**. ID của VPC hiện tại trên tài khoản AWS của bạn, nơi các máy chủ EC2 sẽ được đặt.
*   `subnet_id`: **Bắt buộc**. ID của mạng con công cộng (Public Subnet) nằm trong VPC trên, subnet này phải kết nối ra Internet Gateway.
*   `route_table_id`: **Bắt buộc**. ID của bảng định tuyến gắn với subnet trên. Terraform sẽ tự động thêm một Route định tuyến dải mạng OpenStack App Node thông qua Card mạng (ENI) của máy chủ AWS VPN Gateway.

### 2.2. Kết nối VPN an toàn (Rất quan trọng)
*   `openstack_vpn_public_cidr`: **Bắt buộc**. Địa chỉ IP WAN công cộng thật của máy tính chạy OpenStack AIO của bạn (định dạng `x.x.x.x/32`). Lấy IP này bằng lệnh:
    ```bash
    curl -fsS https://checkip.amazonaws.com
    ```
    *Lưu ý: Không dùng IP mạng nội bộ hoặc OpenStack Floating IP ở đây. Đây là IP để cho phép kết nối WireGuard qua cổng UDP 51820.*

### 2.3. Máy chủ ảo & SSH Key
*   `public_key_path`: Đường dẫn đến file SSH Public Key để đẩy lên AWS. Hiện lab dùng `"~/.ssh/vpn_key.pub"`. Đảm bảo khóa đã tồn tại:
    ```bash
    ssh-keygen -t ed25519 -f ~/.ssh/vpn_key -N ""
    ```
*   `keypair_name`: Tên của AWS EC2 Key pair hiển thị trên AWS Console (mặc định: `"aws_vpn_key"`).
*   `instance_type`: Cấu hình dòng máy chủ EC2 cho gateway, WAF, app, DB và VPN (mặc định: `"t3.micro"`).
*   `vpn_node_name`, `waf_node_name`, `app_node_name`, `db_node_name`, `gateway_node_name`: Tên thẻ (Name Tag) gán cho các máy ảo để tiện phân biệt trên AWS Console.

---

## 3. Quy trình thực hiện triển khai

1.  **Cấu hình biến**: Tạo và chỉnh sửa file `terraform.tfvars` theo hướng dẫn ở Mục 2.
2.  **Khởi tạo Terraform & download provider**:
    ```bash
    terraform init
    ```
3.  **Kiểm tra tính hợp lệ của cấu hình**:
    ```bash
    terraform validate
    ```
4.  **Xem trước hạ tầng sẽ tạo**:
    ```bash
    terraform plan
    ```
5.  **Triển khai thực tế**:
    ```bash
    terraform apply
    ```
    *(Nhập `yes` để đồng ý khởi tạo).*

---

## 4. Các thông tin thu được (Outputs)
Khi apply thành công, bạn sẽ nhận được các thông tin sau để điền vào cấu hình Ansible:
*   `vpn_public_ip`: IP công cộng của AWS VPN Gateway.
*   `gateway_public_ip`: IP công cộng của AWS Gateway.
*   `waf_private_ip`: IP private của AWS WAF Node.
*   `app_private_ip`: IP private của AWS App Node.
*   `db_private_ip`: IP private của AWS DB Node, dùng để điền vào `aws_db_private_ip` và `ansible_host` của `aws-db` trong Ansible.
*   `vpn_network_interface_id`: ID của Card mạng AWS VPN Gateway (được dùng để định tuyến cho VPN).
