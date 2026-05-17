# SIEM Hybrid Cloud Command Guide

Guide này mô tả thứ tự chạy từ một repo mới clone để dựng lại lab SIEM hybrid cloud.

Kiến trúc hiện tại:

- OpenStack AIO trên laptop: App Node và OpenStack VPN Node.
- AWS: WAF Node và AWS VPN Node.
- Local laptop: Elasticsearch và Kibana bằng Docker.
- Logstash: chạy trên OpenStack VPN Node.
- Filebeat trên App/WAF gửi log về `10.0.1.254:5044`, sau đó Logstash forward về Elasticsearch local `172.10.10.1:9200`.

Lưu ý quan trọng về OpenStack AIO laptop: `172.10.10.0/24` là provider/external network giả lập bằng `br-exnat + veth + NAT`, không phải public Internet thật. Vì vậy AWS không thể truy cập trực tiếp OpenStack floating IP `172.10.10.x`. Thiết kế hiện tại giống các project tham khảo: AWS VPN Node giữ public WireGuard endpoint, OpenStack VPN Node chủ động kết nối ra AWS public IP, AWS peer không hard-code endpoint OpenStack.

## 0. Điều kiện ban đầu

Chạy trên laptop OpenStack AIO/local SIEM host.

Cần có:

- Terraform đã cài và đang auth được AWS/OpenStack.
- Ansible đã cài.
- Docker + Docker Compose đã cài.
- SSH keys:
  - `~/.ssh/openstack_key`
  - `~/.ssh/aws_vpn_key`
- OpenStack AIO đã có bridge/NAT theo `Fundemental.md`: `br-exnat=172.10.10.1/24`, provider floating IP pool `172.10.10.200-250`.

Kiểm tra nhanh:

```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM
ip -br addr | grep -E 'wlp0s20f3|br-exnat|veth'
docker compose version
ansible --version
terraform version
```

Output mong đợi:

- Thấy `br-exnat` có IP `172.10.10.1/24`.
- Docker Compose, Ansible, Terraform in version không lỗi.

## 1. Terraform OpenStack

Mục đích: tạo OpenStack App Node và OpenStack VPN Node. Terraform chỉ tạo hạ tầng, không cài Docker/Juice Shop/ELK.

```bash
source /home/nhatnguyen/kolla-venv/bin/activate
source /etc/kolla/admin-openrc.sh 
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/terraform/openstack
terraform init
terraform apply
terraform output
```

Khi `terraform apply` hỏi confirm, nhập:

```text
yes
```

Output mong đợi:

```text
Apply complete! Resources: 21 added, 0 changed, 0 destroyed.
app_node_ip = "10.0.1.x"
vpn_public_ip = "172.10.10.x"
```

Cần ghi lại:

- `OPENSTACK_APP_IP`: ví dụ `10.0.1.245`
- `OPENSTACK_VPN_FIP`: ví dụ `172.10.10.227`

## 2. Terraform AWS

Mục đích: tạo AWS WAF Node, AWS VPN Node, route AWS đến OpenStack app subnet qua ENI của AWS VPN Node.

Trong laptop AIO, OpenStack FIP `172.10.10.x` không phải public source trên Internet. Security group WireGuard trên AWS phải cho phép public source thật của laptop/router NAT. Lấy IP này bằng một trong hai cách:

```bash
curl -fsS https://checkip.amazonaws.com
```

Hoặc sau khi VPN đã handshake, đọc endpoint mà AWS thấy:

```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/ansible
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible -i inventories/production/hosts.yml aws_vpn -b -m shell -a 'wg show wg0 endpoints'
```

Apply AWS với `/32` của IP đó:

```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/terraform/aws
terraform init
terraform apply -var 'openstack_vpn_public_cidr=<REAL_LAPTOP_WAN_IP>/32'
terraform output
```

Output mong đợi:

```text
Apply complete! Resources: 8 added, 0 changed, 0 destroyed.
vpn_public_ip = "x.x.x.x"
vpn_private_ip = "172.31.x.x"
waf_public_ip = "x.x.x.x"
waf_private_ip = "172.31.x.x"
vpn_network_interface_id = "eni-..."
```

Cần ghi lại:

- `AWS_VPN_PUBLIC_IP`
- `AWS_WAF_PUBLIC_IP`
- `AWS_VPN_PRIVATE_IP`
- `AWS_WAF_PRIVATE_IP`

Trong trường hợp IP nhà mạng thay đổi, update lại biến `openstack_vpn_public_cidr` và chạy lại `terraform apply`, sau đó verify WireGuard handshake.

## 3. Cập nhật Ansible inventory

File inventory thật bị ignore bởi git:

```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/ansible
cp inventories/production/hosts.example.yml inventories/production/hosts.yml
nano inventories/production/hosts.yml
```

Điền các giá trị:

- `aws-vpn.ansible_host`: `AWS_VPN_PUBLIC_IP`
- `openstack-vpn.ansible_host`: `OPENSTACK_VPN_FIP`
- `openstack-vpn.wireguard_endpoint`: để chuỗi rỗng `""`
- `aws-waf.ansible_host`: `AWS_WAF_PUBLIC_IP`
- `openstack-app.ansible_host`: `OPENSTACK_APP_IP`

Ý nghĩa của `wireguard_endpoint: ""`: khi sinh config cho AWS VPN Node, peer OpenStack không có `Endpoint = 172.10.10.x:51820`. AWS sẽ đợi OpenStack gửi gói đầu tiên, đúng với môi trường OpenStack AIO sau NAT. Ngược lại, config trên OpenStack VPN Node vẫn có endpoint AWS public IP.

Nếu SSH vào App Node phải đi qua OpenStack VPN Node, dùng `ProxyCommand` rõ key:

```yaml
ansible_ssh_common_args: "-o ProxyCommand='ssh -i ~/.ssh/openstack_key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -W %h:%p ubuntu@<OPENSTACK_VPN_FIP>'"
```

Kiểm tra inventory:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible -i inventories/production/hosts.yml all -m ping
```

Output mong đợi:

```text
aws-vpn | SUCCESS
openstack-vpn | SUCCESS
aws-waf | SUCCESS
openstack-app | SUCCESS
```

Nếu App fail nhưng OpenStack VPN success, kiểm tra lại `ProxyCommand`.

## 4. Cập nhật biến Ansible

Mở file:

```bash
nano inventories/production/group_vars/all.yml
```

Cần đúng các giá trị quan trọng:

```yaml
app_backend_host: <OPENSTACK_APP_IP>
openstack_vpn_app_ip: 10.0.1.254
logstash_host: "{{ openstack_vpn_app_ip }}"
logstash_port: 5044
elasticsearch_host: 172.10.10.1
elasticsearch_port: 9200
```

Ý nghĩa:

- `app_backend_host`: IP App Node để Nginx WAF reverse proxy tới Juice Shop qua VPN.
- `logstash_host`: địa chỉ Logstash trên OpenStack VPN Node. App Node đi nội bộ OpenStack; WAF Node đi qua WireGuard.
- `elasticsearch_host`: địa chỉ laptop local trên `br-exnat`; Logstash trên OpenStack VPN Node ghi log về đây.

## 5. Deploy local Elasticsearch/Kibana

Mục đích: chạy Elasticsearch và Kibana trên laptop local. Logstash không chạy ở Docker local nữa.
Kibana compose có các encryption key cố định để alerting có thể chạy ổn định sau restart.

```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/elk
sudo sysctl -w vm.max_map_count=262144
sudo docker compose up -d --remove-orphans
sudo docker compose ps
```

Output mong đợi:

```text
siem-elasticsearch   Up ... healthy   172.10.10.1:9200->9200/tcp
siem-kibana          Up ... healthy   127.0.0.1:5601->5601/tcp
```

Verify:

```bash
sudo docker exec siem-elasticsearch curl -fsS http://localhost:9200/_cluster/health?pretty
sudo docker exec siem-kibana curl -fsS http://localhost:5601/api/status | head -c 1000
```

Output mong đợi:

- Elasticsearch `status` là `green` hoặc `yellow`.
- Kibana `overall.level` là `available`.

## 6. Deploy WireGuard VPN gateways

Mục đích: cài WireGuard + iptables trên AWS VPN Node và OpenStack VPN Node.

```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/ansible
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible-playbook network_vpn.yml
```

Output mong đợi:

```text
PLAY RECAP
aws-vpn       : failed=0 unreachable=0
openstack-vpn : failed=0 unreachable=0
```

Kiểm tra WireGuard:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible -i inventories/production/hosts.yml vpn_gateways -b -m shell -a 'wg show; ip route'
```

Output tốt:

- OpenStack peer có `endpoint: <AWS_VPN_PUBLIC_IP>:51820`.
- AWS peer không cần hiện `endpoint` ban đầu, nhưng sau handshake sẽ học endpoint thực của OpenStack.
- Có `latest handshake` và `transfer` tăng ở cả hai đầu.

## 7. Deploy Logstash trên OpenStack VPN Node

Mục đích: cài Logstash trực tiếp trên OpenStack VPN Node, lắng nghe Beats `0.0.0.0:5044`, ghi sang Elasticsearch local `172.10.10.1:9200`.

```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/ansible
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible-playbook logstash_vpn.yml
```

Output mong đợi:

```text
PLAY RECAP
openstack-vpn : failed=0 unreachable=0
```

Verify Logstash và đường ghi về Elasticsearch:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible -i inventories/production/hosts.yml openstack_vpn -b -m shell -a \
'systemctl is-active logstash; ss -tlnp | grep :5044; curl -fsS http://172.10.10.1:9200/_cluster/health?pretty'
```

Output mong đợi:

- `logstash` là `active`.
- Có socket listen `:5044`.
- Elasticsearch trả về JSON health.

## 8. Deploy App Node và WAF Node

Mục đích:

- App Node: Docker + OWASP Juice Shop + Filebeat.
- WAF Node: Nginx reverse proxy + Filebeat.
- Filebeat hai node gửi về OpenStack VPN Node `10.0.1.254:5044`.

```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/ansible
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible-playbook app.yml waf.yml
```

Output mong đợi:

```text
PLAY RECAP
openstack-app : failed=0 unreachable=0
aws-waf       : failed=0 unreachable=0
```

Kiểm tra App Node:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible -i inventories/production/hosts.yml app_nodes -b -m shell -a \
'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"; systemctl is-active filebeat; journalctl -u filebeat -n 30 --no-pager | grep -E "10.0.1.254:5044|established|Failed" || true'
```

Output mong đợi:

- Có container `juiceshop`.
- `filebeat` là `active`.
- Log Filebeat có connection established đến `10.0.1.254:5044`.

Kiểm tra WAF Node:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible -i inventories/production/hosts.yml waf_nodes -b -m shell -a \
'nginx -t; systemctl is-active nginx; systemctl is-active filebeat; journalctl -u filebeat -n 30 --no-pager | grep -E "10.0.1.254:5044|established|Failed" || true'
```

Output mong đợi:

- `nginx -t` successful.
- `nginx` active.
- `filebeat` active và kết nối được Logstash nếu WireGuard đã handshake.

## 9. Verify ingestion vào Elasticsearch

Tạo log mới:

```bash
curl -I --max-time 10 http://<AWS_WAF_PUBLIC_IP>/ || true
```

Kiểm tra index:

```bash
sudo docker exec siem-elasticsearch curl -fsS \
  'http://localhost:9200/_cat/indices/siem-hybrid-*?v'
```

Output mong đợi:

```text
health status index                  docs.count
yellow open   siem-hybrid-YYYY.MM.DD ...
```

Kiểm tra log App/WAF:

```bash
sudo docker exec siem-elasticsearch curl -fsS \
  'http://localhost:9200/siem-hybrid-*/_search?filter_path=hits.total.value,aggregations.roles.buckets,aggregations.hosts.buckets' \
  -H 'Content-Type: application/json' \
  -d '{"size":0,"aggs":{"roles":{"terms":{"field":"fields.node_role.keyword","size":10}},"hosts":{"terms":{"field":"host.name.keyword","size":10}}}}'
```

Output mong đợi:

```json
{
  "hits": {"total": {"value": 1}},
  "aggregations": {
    "roles": {
      "buckets": [
        {"key": "app", "doc_count": 1},
        {"key": "waf", "doc_count": 1}
      ]
    }
  }
}
```

Số lượng `doc_count` tùy vào log thực tế, không cần trùng ví dụ.

## 10. Provision Kibana data view, dashboard và alert

Mục đích: tạo sẵn Kibana data view `siem-hybrid-*`, dashboard tổng quan và rule cảnh báo khi pipeline không có log mới trong 10 phút.

```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/elk
python3 kibana/provision_kibana.py
```

Output mong đợi:

```text
Provisioned Kibana data view, dashboard, and alert rule.
Dashboard: http://127.0.0.1:5601/app/dashboards#/view/siem-hybrid-overview
Data view: siem-hybrid-data-view
Alert rule: SIEM Hybrid - no logs in 10 minutes
```

Verify bằng API:

```bash
curl -fsS http://127.0.0.1:5601/api/data_views -H 'kbn-xsrf: true'
curl -fsS 'http://127.0.0.1:5601/api/saved_objects/_find?type=dashboard&search=SIEM%20Hybrid%20Overview&search_fields=title' -H 'kbn-xsrf: true'
curl -fsS 'http://127.0.0.1:5601/api/alerting/rules/_find?search=SIEM%20Hybrid%20-%20no%20logs%20in%2010%20minutes&search_fields=name' -H 'kbn-xsrf: true'
```

## 11. Chạy tất cả bằng site.yml

Sau khi inventory và `group_vars/all.yml` đúng, có thể chạy một lệnh:

```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/ansible
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible-playbook site.yml
```

Thứ tự trong `site.yml`:

1. `network_vpn.yml`
2. `logstash_vpn.yml`
3. `app.yml`
4. `waf.yml`

## 12. Debug nhanh

Kiểm tra local OpenStack AIO bridge/NAT:

```bash
ip -br addr | grep -E 'br-exnat|veth|wlp0s20f3'
sudo iptables -t nat -S | grep 172.10.10 || true
sudo iptables -S FORWARD | grep -E 'br-exnat|wlp0s20f3' || true
```

Kiểm tra WireGuard:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible -i inventories/production/hosts.yml vpn_gateways -b -m shell -a \
'wg show; ip route; iptables -S; iptables -t nat -S'
```

Đọc kết quả:

- Có `latest handshake`: VPN đang thông.
- `0 B received`: chưa có UDP hai chiều; kiểm tra AWS SG UDP/51820 và OpenStack VPN có endpoint AWS public IP.
- AWS VPN peer không có endpoint cố định là bình thường trong lab này.

Kiểm tra Logstash trên OpenStack VPN Node:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible -i inventories/production/hosts.yml openstack_vpn -b -m shell -a \
'systemctl status logstash --no-pager; journalctl -u logstash -n 80 --no-pager'
```

Kiểm tra Filebeat App:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible -i inventories/production/hosts.yml app_nodes -b -m shell -a \
'systemctl is-active filebeat; journalctl -u filebeat -n 50 --no-pager | grep -E "10.0.1.254:5044|established|Failed" || true'
```

Kiểm tra Filebeat WAF:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible -i inventories/production/hosts.yml waf_nodes -b -m shell -a \
'systemctl is-active filebeat; journalctl -u filebeat -n 50 --no-pager | grep -E "10.0.1.254:5044|established|Failed" || true'
```

## 13. Stop / clean local SIEM

Dừng Elasticsearch/Kibana local:

```bash
cd /home/nhatnguyen/Desktop/NT524/NT524_2026/Project/SIEM/elk
sudo docker compose down
```

Xóa cả Elasticsearch data volume:

```bash
sudo docker compose down -v
```

Cẩn thận: `down -v` xóa index `siem-hybrid-*`.
