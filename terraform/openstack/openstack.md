# Hướng dẫn sử dụng Terraform cho OpenStack

Tài liệu này hướng dẫn cách sử dụng Terraform để triển khai hạ tầng trên OpenStack trong dự án này.

## 1. Cấu trúc thư mục

Hạ tầng được tổ chức theo dạng module:
- `main.tf`: File chính gọi các module.
- `provider.tf`: Cấu hình provider OpenStack.
- `variables.tf`: Khai báo biến.
- `terraform.tfvars`: Chứa giá trị biến.
- `modules/`: (network, security_group, compute).

## 2. Chuẩn bị tài nguyên trên OpenStack

Trước khi chạy Terraform, bạn cần chuẩn bị các tài nguyên cơ bản sau bằng OpenStack CLI hoặc Dashboard.

### 2.1. Thiết lập thông tin xác thực
Kích hoạt môi trường Kolla và load biến admin:
```bash
source ~/kolla-venv/bin/activate
source /etc/kolla/admin-openrc.sh
```

### 2.2. Tạo SSH Key
Terraform sẽ sử dụng file key tại `/.ssh/openstack_key.pub` để đẩy lên OpenStack.
```bash
# Tạo cặp key mới nếu chưa có
ssh-keygen -t ed25519 -f ~/.ssh/openstack_key -N ""
```

### 2.3. Tạo Image, Flavor và Public Network
Nếu OpenStack của bạn chưa có sẵn, hãy chạy các lệnh sau:

**Tạo Image:**
```bash
# Download Ubuntu cloud image
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img -O ubuntu-24.04.img

# Upload image
openstack image create "Ubuntu-24.04" --file ubuntu-24.04.img --disk-format qcow2 --container-format bare --public
```

**Tạo Flavor:**
```bash
openstack flavor create --id auto --ram 2048 --disk 20 --vcpus 2 m1.small
```

**Tạo Mạng Provider (External):**

```bash
# Tạo external network (provider network)

openstack network create public-net \
  --external \
  --provider-physical-network physnet1 \
  --provider-network-type flat \
  --share
  
# Tạo subnet cho external network
openstack subnet create public-subnet \
  --network public-net \
  --subnet-range 172.10.10.0/24 \
  --gateway 172.10.10.1 \
  --allocation-pool start=172.10.10.200,end=172.10.10.250 \
  --dns-nameserver 8.8.8.8 \
  --no-dhcp
```

*Lưu ý: Lấy ID của `public-net` để điền vào `external_network_id` trong `terraform.tfvars`.*

## 3. Các bước triển khai với Terraform

1. **Cấu hình biến**: Cập nhật `external_network_id` trong `terraform.tfvars`.
2. **Khởi tạo**: `terraform init`
3. **Kiểm tra**: `terraform plan`
4. **Triển khai**: `terraform apply`

## 4. Kiểm tra sau khi khởi tạo

Sau khi lệnh `apply` thành công, bạn cần kiểm tra trạng thái của các máy ảo.

### 4.1. Lấy thông tin IP
Bạn có thể dùng lệnh sau để xem danh sách máy ảo và IP:
```bash
openstack server list
```
- **VPN Gateway**: Sẽ có 2 IP (1 private, 1 Floating IP public).
- **App Node**: Chỉ có 1 IP private (10.0.1.x).

### 4.2. Truy cập SSH vào VPN Gateway
Sử dụng Floating IP để SSH vào máy chủ VPN:
```bash
ssh -i /.ssh/openstack_key ubuntu@<FLOATING_IP_GATEWAY> -J ubuntu@<IP_appnode>
```

# Kiểm tra đã cài Docker chưa
```bash
docker ps -a
```

### 4.4. Kiểm tra Internet và NAT trên App Node
Truy cập vào App Node và thử ping ra ngoài:
```bash
ping google.com
```
Nếu ping thành công, nghĩa là VPN Gateway đã cấu hình NAT và Route chính xác cho App Node.

## 5. Dọn dẹp tài nguyên
```bash
terraform destroy
```
