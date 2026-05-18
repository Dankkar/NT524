# Hướng dẫn sử dụng Terraform cho OpenStack (Refactored)

Tài liệu này hướng dẫn cách cấu hình và sử dụng Terraform để triển khai hạ tầng ảo hóa trên OpenStack phục vụ cho lab SIEM/WAF Hybrid Cloud.

---

## 1. Cấu trúc thư mục hạ tầng

Hạ tầng OpenStack được tổ chức dạng module để dễ tái sử dụng và quản lý:
*   **[main.tf](file:///home/deployer/Downloads/Project/terraform/openstack/main.tf)**: File chính điều phối và truyền biến cho các module con.
*   **[provider.tf](file:///home/deployer/Downloads/Project/terraform/openstack/provider.tf)**: Định nghĩa nhà cung cấp OpenStack.
*   **[variables.tf](file:///home/deployer/Downloads/Project/terraform/openstack/variables.tf)**: Khai báo tất cả các tham số đầu vào.
*   **[terraform.tfvars](file:///home/deployer/Downloads/Project/terraform/openstack/terraform.tfvars)**: **[NƠI CHỈNH SỬA CHÍNH]** Chứa các giá trị cấu hình thực tế cho môi trường của bạn.
*   **modules/**: Gồm 3 module con:
    *   `network`: Quản lý mạng private, subnet, router, cổng và Floating IP.
    *   `security_group`: Quản lý tường lửa/luật bảo mật cho App Node & VPN Node.
    *   `compute`: Khởi tạo SSH keypair, App Node VM và VPN Gateway VM.

---

## 2. Các tham số cần kiểm tra và chỉnh sửa trong `terraform.tfvars`

Để cấu hình phù hợp với hệ thống OpenStack của bạn, hãy mở file **[terraform.tfvars](file:///home/deployer/Downloads/Project/terraform/openstack/terraform.tfvars)** và tùy chỉnh các tham số sau:

### 2.1. Kết nối Mạng ngoài & Floating IP (Quan trọng nhất)
*   `external_network_id`: **Bắt buộc**. Nhập ID của mạng ngoài (External/Public network) trên OpenStack của bạn. Lấy ID bằng cách chạy lệnh:
    ```bash
    openstack network list --external
    ```
*   `floating_ip_pool`: Tên của Pool mạng ngoài để cấp Floating IP (mặc định: `"public-net"` hoặc `"public1"` tùy thuộc môi trường của bạn).

### 2.2. Thông tin SSH Key
*   `keypair_name`: Tên của SSH Keypair sẽ được khai báo trên OpenStack (mặc định: `"vpn_key"`).
*   `public_key_path`: Đường dẫn đến SSH Public Key trên máy local của bạn (mặc định: `"~/.ssh/vpn_key.pub"`). Đảm bảo bạn đã tạo cặp khóa này:
    ```bash
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/vpn_key -N ""
    ```

### 2.3. Máy ảo & Hệ điều hành
*   `image_name`: Tên của Image hệ điều hành Ubuntu đã upload lên OpenStack (mặc định: `"ubuntu22.04"`). Kiểm tra danh sách bằng:
    ```bash
    openstack image list
    ```
*   `flavor_name`: Cấu hình phần cứng cho máy ảo (mặc định: `"m1.small"`). Kiểm tra danh sách bằng:
    ```bash
    openstack flavor list
    ```
*   `app_node_name` & `vpn_node_name`: Tên hiển thị của máy ảo App Node và VPN Gateway trên OpenStack Dashboard.

### 2.4. Địa chỉ IP & Dải mạng nội bộ
*   `private_subnet_cidr`: Dải IP cho mạng kết nối nội bộ của VPN Gateway (mặc định: `"10.0.0.0/24"`).
*   `app_subnet_cidr`: Dải IP cho mạng cách ly của App Node (mặc định: `"10.0.1.0/24"`).
*   `vpn_app_ip`: Địa chỉ IP tĩnh của VPN Gateway đóng vai trò làm Router/Gateway trung chuyển cho App Node (mặc định: `"10.0.1.254"`).
*   `router_name`: Tên của OpenStack Router (mặc định: `"vpn_router"`).

---

## 3. Quy trình thực hiện triển khai

1.  **Thiết lập môi trường xác thực (OpenStack RC)**:
    ```bash
    source ~/kolla-venv/bin/activate
    source /etc/kolla/admin-openrc.sh
    ```
2.  **Di chuyển vào thư mục**:
    ```bash
    cd /home/deployer/Downloads/Project/terraform/openstack
    ```
3.  **Tùy biến cấu hình**: Mở và chỉnh sửa file `terraform.tfvars` theo cấu hình của bạn.
4.  **Khởi tạo Terraform**:
    ```bash
    terraform init
    ```
5.  **Kiểm tra trước hạ tầng**:
    ```bash
    terraform plan
    ```
6.  **Triển khai hạ tầng thực tế**:
    ```bash
    terraform apply
    ```
    *(Gõ `yes` khi được hỏi để xác nhận triển khai).*

---

## 4. Kiểm tra sau khi khởi tạo

Khi chạy `apply` hoàn tất, bạn có thể thực hiện kiểm tra nhanh:

### 4.1. Lấy thông tin IP các máy ảo
```bash
openstack server list
```
*   **VPN Gateway**: Sẽ sở hữu 1 IP private và 1 Floating IP kết nối mạng ngoài.
*   **App Node**: Chỉ sở hữu duy nhất 1 IP nội bộ nằm trong dải `10.0.1.0/24` và không thể kết nối trực tiếp từ mạng ngoài.

### 4.2. SSH qua Jump Host (VPN Gateway)
Do App Node nằm trong mạng cách ly, để SSH vào App Node, bạn cần đi qua VPN Gateway làm bàn đạp (Jump Host):
```bash
ssh -i ~/.ssh/vpn_key ubuntu@<FLOATING_IP_GATEWAY> -J ubuntu@<IP_APP_NODE_PRIVATE>
```

### 4.3. Kiểm tra định tuyến Internet của App Node
Truy cập App Node qua SSH và kiểm tra xem có ping ra Internet được không:
```bash
ping -c 3 google.com
```
*Nếu ping thành công, cơ chế định tuyến NAT (IP Forwarding & MASQUERADE) qua VPN Gateway đã hoạt động chính xác!*

---

## 5. Dọn dẹp tài nguyên
Khi muốn xóa toàn bộ hạ tầng để giải phóng tài nguyên OpenStack:
```bash
terraform destroy
```
