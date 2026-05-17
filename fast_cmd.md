### 1. Các bước dọn dẹp sạch 100%

**ELK - Local (Xóa container và index data):**
```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/elk
sudo docker compose down -v 
```

**Môi trường OpenStack (Xóa máy ảo, network, router, FIP):**
```bash
source /home/nhatnguyen/kolla-venv/bin/activate
source /etc/kolla/admin-openrc.sh 
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/terraform/openstack
terraform destroy -auto-approve
```

**Môi trường AWS (Xóa EC2, VPC, SG, ENI, EIP):**
```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/terraform/aws
terraform destroy -auto-approve
```

*(Tùy chọn) Dọn dẹp SSH known_hosts để lần sau không bị lỗi cảnh báo Man-in-the-middle do IP cũ cấp lại cho máy ảo mới:*
```bash
rm -f ~/.ssh/known_hosts
```

---

### 2. Các bước tạo lại tài nguyên mới 100% cho lần tới

Dựa theo file hướng dẫn cmd_guide.md, bạn chạy tuần tự các bước sau:

**Bước 1: Khởi tạo lại hạ tầng OpenStack**
```bash
source /home/nhatnguyen/kolla-venv/bin/activate
source /etc/kolla/admin-openrc.sh 
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/terraform/openstack
terraform apply -auto-approve
```

**Bước 2: Lấy WAN IP thật của laptop và khởi tạo hạ tầng AWS**
```bash
# Lấy WAN IP hiện tại (đề phòng ISP đổi IP)
curl -fsS https://checkip.amazonaws.com

# Apply AWS với biến WAN IP vừa lấy
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/terraform/aws
terraform apply -var 'openstack_vpn_public_cidr=<WAN_IP_CỦA_BẠN>/32' -auto-approve
```

**Bước 3: Cập nhật lại thông tin dải IP mới cấp cho Ansible**
1. Mở file ansible/inventories/production/hosts.yml và điền các IP tĩnh / Public IP mới lấy được từ kết quả Terraform output.
2. Mở file ansible/inventories/production/group_vars/all.yml để sửa đổi thông tin biến `app_backend_host`.

**Bước 4: Bật lại ELK stack trên máy Local**
```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/elk
sudo sysctl -w vm.max_map_count=262144
sudo docker compose up -d --remove-orphans
```

**Bước 5: Cấu hình phần mềm và VPN với Ansible**
Khởi chạy bộ thiết lập (VPN, Logstash, App, WAF) thông qua file chạy gộp của bạn:
```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/ansible
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible-playbook site.yml
```

**Bước 6: Provision Kibana (Dashboards & Alerts)**
Sau khi các services đã vận hành hoàn chỉnh và có log gửi về:
```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/elk
python3 kibana/provision_kibana.py
```