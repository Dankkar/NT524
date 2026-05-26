# Task Log - Hybrid Cloud NAC/WAF/App/DB

Ngay cap nhat: 2026-05-26

## Cap nhat 2026-05-26

- Da doc lai task log ngay 2026-05-25.
- User da `terraform destroy` OpenStack truoc do; hom nay da apply lai OpenStack thanh cong.
- OpenStack IP moi sau apply:
  - `vpn_public_ip`: `172.10.10.208`
  - `waf_node_ip`: `10.0.2.10`
  - `app_node_ip`: `10.0.1.244`
  - `db_node_ip`: `10.0.1.94`
- Da cap nhat `docs/1.md` sang app moi:
  - Lightweight Flask Auth App.
  - PostgreSQL centralized tren DB node rieng.
  - App nhan identity headers tu oauth2-proxy/Cognito sau nay.
- Da cap nhat `docs/1.md` them entrypoint don gian:
  - user chi vao `abc.net`.
  - `abc.net` dung Route 53 Failover DNS de chon AWS gateway hoac OpenStack gateway.
- Da xoa Ansible role khong con dung:
  - `juice_shop_app`
  - `mongodb_centralized`
- Hien cac role app/DB dang dung la:
  - `simple_auth_app`
  - `postgresql_centralized`
- Da doi WAF template tu `juice_shop_proxy.conf.j2` sang `app_proxy.conf.j2`.
- Da cap nhat `ansible/README.md` va comment Logstash sang app moi.
- Da kiem tra offline:
  - `ansible-playbook -i inventories/production/hosts.yml app.yml --syntax-check`: OK
  - `ansible-playbook -i inventories/production/hosts.yml waf.yml --syntax-check`: OK
  - `terraform -chdir=terraform/openstack validate`: OK
- Da chay `app.yml` tren OpenStack moi: OK.
- Da test:
  - `openstack-app` health local `http://127.0.0.1/healthz`: `{"status":"ok"}`
  - `openstack-waf` goi app private `http://10.0.1.244/healthz`: `{"status":"ok"}`
  - PostgreSQL container `hybrid-auth-postgres`: running.
  - App container `hybrid-auth-app`: running.
- Da chay `waf.yml` toi buoc pull image ECR, nhung bi dung tai ECR:
  - image cu trong Ansible: `742873383494.dkr.ecr.ap-southeast-1.amazonaws.com/my-waf-nginx:latest`
  - AWS credentials hien tai: `arn:aws:iam::211116632423:user/terraform-dev`
  - Pull/describe registry `742873383494` bi `AccessDenied`.
  - ECR registry hien tai `211116632423` van hoat dong va cap login token duoc, nhung repo `my-waf-nginx` hien khong ton tai.
  - Da doi `waf_image` trong `group_vars/all.yml` ve `211116632423.dkr.ecr.ap-southeast-1.amazonaws.com/my-waf-nginx:latest`; can tao repo va push image truoc khi rerun WAF.
- Da bo sung AWS app/WAF theo topology giong OpenStack:
  - Terraform AWS tao them `aws-app-node`.
  - Terraform AWS tao ECR repo `211116632423.dkr.ecr.ap-southeast-1.amazonaws.com/my-waf-nginx`.
  - AWS VPN public IP: `54.169.109.49`
  - AWS WAF public/private IP: `13.229.165.24` / `172.31.4.221`
  - AWS app public/private IP: `13.212.148.187` / `172.31.8.161`
  - AWS app public HTTP bi chan boi SG; user phai di qua WAF.
- Da cau hinh WireGuard AWS <-> OpenStack:
  - AWS app ket noi duoc PostgreSQL OpenStack `10.0.1.94:5432` qua VPN.
  - Sua `openstack_vpn_app_ip` tu `10.0.1.254` sang `10.0.2.254` vi topology moi dat VPN gateway tren WAF transit net.
  - Them DB allowed CIDR `10.0.2.0/24` cho PostgreSQL vi OpenStack VPN NAT traffic AWS ra transit IP.
- Da deploy AWS app bang `app.yml --limit aws-app`: OK.
- Da build va push WAF image len ECR:
  - tag: `211116632423.dkr.ecr.ap-southeast-1.amazonaws.com/my-waf-nginx:latest`
  - digest: `sha256:3dd414176bc7d5e07d6f75caefc4ccc0b0dc78a879de4a5637a1cef0a6ad1e3d`
- Da deploy WAF bang `waf.yml` cho ca AWS va OpenStack: OK.
- Da test WAF/app:
  - AWS WAF public `http://13.229.165.24/healthz`: `{"status":"ok"}`
  - AWS WAF local -> AWS app private: `{"status":"ok"}`
  - OpenStack WAF local -> OpenStack app private: `{"status":"ok"}`
  - SQLi test qua AWS WAF: HTTP `403`
  - SQLi test qua OpenStack WAF: HTTP `403`

## Muc tieu gan

- Trien khai topology OpenStack dung yeu cau: `VPN Gateway -> WAF -> App/DB`.
- Tao DB node rieng tren OpenStack thay vi chay database chung instance voi app.
- Thay NodeGoat bang web app nhe co login va database centralized.
- Chua lam Cognito trong ngay nay; app duoc thiet ke san de nhan identity headers tu oauth2-proxy/Cognito sau nay.

## Da xong

### Terraform OpenStack

- Da them `waf_private_net` / `waf_private_subnet` lam transit network giua VPN Gateway va WAF.
  - CIDR: `10.0.2.0/24`
  - VPN Gateway transit IP: `10.0.2.254`
  - WAF transit IP: `10.0.2.10`
- Da doi topology:
  - `vpn-gateway` chi nam trong `vpn_private_net` va `waf_private_net`.
  - `waf-node` co 2 NIC: `waf_private_net` va `app_private_net`.
  - `app-node` chi nam trong `app_private_net`.
  - `db-node` moi chi nam trong `app_private_net`.
- Da tao `db-node` rieng cho centralized database.
  - DB IP hien tai: `10.0.1.94`
- Da chuyen default gateway cua app/db sang WAF:
  - `app-node` default route: `via 10.0.1.254`
  - `db-node` default route: `via 10.0.1.254`
- Da xac minh OpenStack server:
  - `vpn-gateway ACTIVE`: floating IP `172.10.10.208`, `waf_private_net=10.0.2.254`
  - `waf-node ACTIVE`: `waf_private_net=10.0.2.10`, `app_private_net=10.0.1.254`
  - `app-node ACTIVE`: `app_private_net=10.0.1.244`
  - `db-node ACTIVE`: `app_private_net=10.0.1.94`
- Da chay `terraform plan -detailed-exitcode` sau apply va co luc ket qua la `No changes`.

### Ansible Inventory / Vars

- Da cap nhat `ansible/inventories/production/hosts.yml`:
  - `openstack-waf`: `10.0.2.10`, SSH qua `172.10.10.208`
  - `openstack-app`: `10.0.1.244`, SSH qua `172.10.10.208`
  - `openstack-db`: `10.0.1.94`, SSH qua `172.10.10.208`
- Da them group `db_nodes`.
- Da cap nhat `group_vars/all.yml` cho app nhe va PostgreSQL:
  - App image local: `hybrid-auth-app:local`
  - DB host: `10.0.1.94`
  - DB container: `hybrid-auth-postgres`
  - DB data dir: `/opt/hybrid-auth/postgres/data`

### App / Database

- Da tao role `postgresql_centralized`.
  - Chay PostgreSQL container tren `db-node`.
  - Data mount ra host tai `/opt/hybrid-auth/postgres/data`.
- Da tao role `simple_auth_app`.
  - Web app Flask + Gunicorn nhe, build local Docker image tren app node.
  - Co login dev de test truoc Cognito.
  - Co ho tro identity headers cho Cognito/oauth2-proxy sau nay:
    - `X-Auth-Request-Email`
    - `X-Auth-Request-User`
    - `X-Auth-Request-Preferred-Username`
  - Auto create/update user theo email.
  - Co private notes luu vao PostgreSQL de test centralized data.
- Da deploy `app.yml` thanh cong:
  - `openstack-db`: PostgreSQL container da chay.
  - `openstack-app`: Flask app container da chay.
  - NodeGoat va MongoDB local cu tren app node da bi xoa container de giam RAM.
- Da test:
  - App health local tren app node: `{"status":"ok"}`
  - Gia lap Cognito header tao user `demo@example.com`.
  - DB co user count = `1`.
  - WAF node reach duoc app health qua `http://10.0.1.244/healthz`.

## Dang do / Chua xong

### Cognito / NAC

- Chua lam Cognito/oauth2-proxy.
- App moi da san sang nhan identity headers tu gateway/oauth2-proxy.
- Buoc sau:
  - them controller/oauth2-proxy,
  - cau hinh Cognito Hosted UI,
  - forward identity headers xuong WAF/app.

### Terraform security group cho WAF egress qua VPN

- Da fix va test runtime.
- Nguyen nhan cu:
  - `vpn_sg` co rule allow app subnet `10.0.1.0/24`.
  - Nhung traffic tu WAF transit IP `10.0.2.10` di qua VPN Gateway co source thuoc `10.0.2.0/24`.
  - `vpn_sg` luc dau chua allow `10.0.2.0/24`, nen apt/curl tu WAF bi treo/timeout.
- Da them va apply Terraform:
  - `openstack_networking_secgroup_rule_v2.vpn_allow_waf_net`
  - allow `var.waf_subnet_cidr` vao `vpn_sg`

### WAF Ansible

- Da sua va deploy `nginx_waf` thanh cong tren AWS WAF va OpenStack WAF.
  - Dung `docker.io` tu Ubuntu repo.
  - Chay WAF bang `docker run --network host` thay vi `docker compose`.
  - Dung image ECR moi: `211116632423.dkr.ecr.ap-southeast-1.amazonaws.com/my-waf-nginx:latest`
- Da test health va SQLi block 403 tren ca hai WAF.

## Viec can lam tiep ngay mai

1. Them controller/oauth2-proxy va Cognito Hosted UI.
2. Tao Route 53 failover record `abc.net`:
   - primary: AWS WAF/gateway endpoint `13.229.165.24`
   - secondary: OpenStack gateway endpoint sau khi co public gateway/controller
3. Bo sung health endpoint cho gateway/controller neu can tach khoi `/healthz` cua app.
4. Test failover/failback voi cung PostgreSQL centralized.

## Ghi chu quan trong

- Hien tai AWS app va OpenStack app deu dung chung PostgreSQL centralized tren OpenStack.
- AWS app public HTTP bi chan; duong user hop le hien tai la qua AWS WAF public IP.
- OpenStack WAF hien test noi bo; can controller/public entrypoint rieng neu muon Route 53 secondary tro truc tiep vao OpenStack.
- Neu recreate Terraform, cap nhat lai `hosts.yml` theo output moi.
