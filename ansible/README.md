# SIEM Hybrid Network/VPN Ansible

Ngày cập nhật: 2026-05-30

## Trạng thái hiện tại

- Inventory thật: `inventories/production/hosts.yml`.
- OpenStack hiện tại:
  - `openstack-vpn` / `openstack-gateway`: `172.10.10.209`
  - `openstack-waf`: `10.0.2.10`
  - `openstack-app`: `10.0.1.214`
- AWS hiện tại:
  - `aws-gateway`: `122.248.227.98`
  - `aws-vpn`: `54.169.109.49`
  - `aws-waf`: `172.31.4.221`
  - `aws-app`: `172.31.8.161`
- AWS DB mới:
  - Terraform đã tạo EC2 `aws-db-node` riêng.
  - Private IP: `172.31.3.61`.
  - `aws-db` là PostgreSQL primary duy nhất.
- OpenStack DB đã được loại khỏi topology; OpenStack app đi AWS DB qua OpenStack WAF/VPN.
- Đã chạy Ansible thành công cho toàn hệ thống: `network_vpn.yml`, `app.yml`, `waf.yml`, `gateway.yml`, `logstash_vpn.yml`.
- Đã chạy `network_vpn.yml` end-to-end bằng key `~/.ssh/vpn_key`; WireGuard hai cloud đã handshake thành công.
- Đã thêm TCP MSS clamp trên WireGuard gateways để tránh treo TCP lớn qua tunnel, đặc biệt là PostgreSQL và logging.
- Public key WireGuard hiện tại của OpenStack VPN đã được cấu hình ở AWS VPN:

```text
gaGs+OT8PGNs1PCvhcYtPwVyCfjJ+B3ZYqrYqLCiRHc=
```

## Cách chạy thủ công

Do thư mục share đang world-writable nên Ansible bỏ qua `ansible.cfg`. Khi chạy thủ công, dùng rõ inventory và roles path:

Lưu ý: không còn deploy `openstack-db`. OpenStack app vẫn dùng `DATABASE_URL` về AWS DB primary, nhưng route DB phải đi qua OpenStack WAF rồi OpenStack/AWS VPN.

```bash
cd ansible
ANSIBLE_ROLES_PATH=roles \
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible-playbook -i inventories/production/hosts.yml app.yml

ANSIBLE_ROLES_PATH=roles \
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible-playbook -i inventories/production/hosts.yml waf.yml --limit openstack-waf

ANSIBLE_ROLES_PATH=roles \
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible-playbook -i inventories/production/hosts.yml gateway.yml --limit openstack-gateway

ANSIBLE_ROLES_PATH=roles \
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible-playbook -i inventories/production/hosts.yml logstash_vpn.yml --limit openstack-vpn
```

## PostgreSQL và DB Flow

Role `postgresql_centralized` hiện chỉ deploy AWS PostgreSQL primary:

- `aws-db` là PostgreSQL primary duy nhất trên EC2 DB riêng.
- AWS DB đã được tạo và triển khai tại `172.31.3.61`.
- OpenStack app `10.0.1.214` đọc/ghi AWS DB qua luồng `OpenStack App -> OpenStack WAF -> OpenStack VPN -> AWS VPN -> AWS DB`.
- OpenStack WAF ghi log riêng packet request TCP/5432 tới AWS DB tại `/var/log/openstack-db-flow.log`; Filebeat gửi về Logstash và index `siem-db-flow-*`.

Kiểm tra DB flow từ OpenStack app:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible -i inventories/production/hosts.yml openstack-app -b -m shell \
  -a 'curl -fsS http://127.0.0.1/healthz'

ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
ansible -i inventories/production/hosts.yml openstack-waf -b -m shell \
  -a 'tail -n 20 /var/log/openstack-db-flow.log'
```

This Ansible layer configures the current hybrid cloud deployment.

Implemented layers:

- WireGuard site-to-site VPN.
- Gateway Nginx + oauth2-proxy.
- WAF Nginx + ModSecurity + OWASP CRS.
- Lightweight Flask app and AWS PostgreSQL primary.
- Filebeat on gateway/WAF/app/VPN nodes.
- Logstash on the OpenStack VPN node.

The Feedback API and ML rule export are local controller scripts under `scripts/`.
GitHub Actions deploy has been removed. Use Ansible from the controller for WAF rule updates and full WAF redeploys.

## Order

1. Apply OpenStack Terraform and record `vpn_public_ip`, `waf_transit_ip`, and `app_node_ip`.
2. Apply AWS Terraform with `openstack_vpn_public_cidr=<REAL_LAPTOP_WAN_IP>/32` for the laptop OpenStack AIO lab. This is the real NAT/WAN source IP, not the OpenStack floating IP.
3. Replace the `CHANGE_ME_*` values in `inventories/production/hosts.yml`.
4. Keep `openstack-vpn.wireguard_endpoint: ""` so AWS does not try to dial the non-public OpenStack floating IP.
5. Run the VPN playbook:

```bash
ansible-playbook network_vpn.yml
```

6. Deploy Logstash on the OpenStack VPN node:

```bash
ansible-playbook logstash_vpn.yml
```

7. Deploy AWS PostgreSQL primary and the App nodes:

```bash
ansible-playbook app.yml
```

8. Deploy the WAF reverse proxy node:

```bash
ansible-playbook waf.yml
```

Or run all configured stages:

```bash
ansible-playbook site.yml
```

## WAF Rule Updates After Feedback/ML

When only `RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf` changes, do not rebuild the WAF image. Export the tuned rule locally, then copy it to AWS WAF and OpenStack WAF:

```bash
cd /home/deployer/Downloads/Project/modsec-learn
~/modsec-ai-venv/bin/python ../scripts/run_training.py
~/modsec-ai-venv/bin/python ../scripts/export_tuned_rules.py \
  --model linear_svc_pl4_l1.joblib \
  --threshold 1e-5

cd /home/deployer/Downloads/Project
ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-cp \
/home/deployer/kolla-venv/bin/ansible-playbook \
  -i ansible/inventories/production/hosts.yml \
  ansible/waf.yml \
  --tags update_rules
```

Run the full `ansible/waf.yml` playbook only when the WAF container image/config stack itself changes.

## Expected Tunnel

- AWS VPN WireGuard IP: `10.200.0.1`
- OpenStack VPN WireGuard IP: `10.200.0.2`
- AWS VPC CIDR: `172.31.0.0/16`
- OpenStack WAF transit CIDR: `10.0.2.0/24`
- OpenStack App/DB CIDR: `10.0.1.0/24`

The OpenStack VPN gateway routes traffic to the WAF transit network. App and DB nodes sit behind the WAF on the app private network, so inbound app traffic should pass through VPN -> WAF -> App.

## Current App/WAF Layer

- AWS DB node runs PostgreSQL primary in Docker with persistent data under `/opt/hybrid-auth/postgres/data`.
- App nodes run the lightweight Flask auth app in Docker, exposed on port `80`, using PostgreSQL through `DATABASE_URL=postgresql://...@172.31.3.61:5432/hybrid_auth`.
- WAF node runs Nginx/ModSecurity as a reverse proxy to the app private IP.
- OpenStack WAF also logs OpenStack app DB requests to AWS DB with prefix `OPENSTACK_APP_TO_AWS_DB`.
- Logstash runs on the OpenStack VPN node and writes to Elasticsearch on the laptop at `172.10.10.1:9200`.
- Filebeat is installed on gateway, WAF, app and VPN nodes.
- Filebeat is configured to send to `{{ logstash_host }}:{{ logstash_port }}` from `group_vars/all.yml`; currently this resolves to `10.0.2.254:5044`.

## Sign Out

Nút Sign Out trong app redirect theo chuỗi:

```text
/oauth2/sign_out -> Cognito /logout -> https://app.nt524.io.vn/
```

Luồng này clear cookie của `oauth2-proxy` và session Cognito Hosted UI. Nếu chỉ clear session trong app, gateway vẫn gửi header `X-Auth-Request-*` và người dùng sẽ bị đăng nhập lại ngay.
