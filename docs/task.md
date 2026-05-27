# Task Log - Hybrid Cloud NAC/WAF/App/DB

Ngay cap nhat: 2026-05-27

## Cap nhat 2026-05-27 - Domain nt524.io.vn

- Da doi Route 53 failover tu domain lab `app.hybrid-lab.test` sang domain that `app.nt524.io.vn`.
- Da apply Terraform AWS thanh cong. Route 53 thay hosted zone cu `hybrid-lab.test` bang hosted zone moi `nt524.io.vn`.
- Failover record hien tai:
  - FQDN: `app.nt524.io.vn`
  - Primary AWS gateway: `122.248.227.98`
  - Secondary OpenStack gateway: `172.10.10.208`
  - AWS health check ID: `f8c7d0d4-b6fc-4311-b5bd-2c5fe44e3ed9`
- Route 53 authoritative nameservers moi can tro o nha dang ky domain:
  - `ns-1270.awsdns-30.org`
  - `ns-2018.awsdns-60.co.uk`
  - `ns-385.awsdns-48.com`
  - `ns-916.awsdns-50.net`
- Test authoritative DNS:
  - `dig +short @ns-1270.awsdns-30.org app.nt524.io.vn A`: `122.248.227.98`
- Public resolver hien tai van tra `125.235.4.59`, nen can delegate nameserver cua `nt524.io.vn` sang Route 53 hoac cho DNS cache het han.

## Cap nhat 2026-05-27 - Cognito / oauth2-proxy

- Da them Terraform Cognito:
  - File moi: `terraform/aws/cognito.tf`
  - User Pool: `hybrid-auth-users`
  - User Pool ID: `ap-southeast-1_Xg1Q3ZUP9`
  - App Client: `hybrid-auth-gateway`
  - App Client ID: `4gn2j0lo07rori6u3snjj6lr4p`
  - Hosted UI base URL: `https://nt524-hybrid-auth-211116632423.auth.ap-southeast-1.amazoncognito.com`
  - Callback URL: `https://app.nt524.io.vn/oauth2/callback`
  - Logout URL: `https://app.nt524.io.vn/`
- Da apply Terraform AWS thanh cong; `terraform plan` sau apply: `No changes`.
- Da them oauth2-proxy/Nginx auth_request vao role `ansible/roles/gateway_proxy`.
  - `oauth2-proxy` chay tren `127.0.0.1:4180`.
  - Nginx gateway bao ve `/` bang `auth_request /oauth2/auth`.
  - `/healthz` van public de Route 53 health check hoat dong.
  - Sau login, gateway forward identity headers xuong WAF/app:
    - `X-Auth-Request-User`
    - `X-Auth-Request-Email`
    - `X-Auth-Request-Preferred-Username`
- Da deploy `ansible/gateway.yml` thanh cong tren:
  - `aws-gateway`
  - `openstack-gateway`
- Da tao user demo trong Cognito:
  - Email/username: `demo@nt524.io.vn`
  - Status: `CONFIRMED`
- Da test:
  - `http://app.nt524.io.vn/healthz` qua AWS gateway: `{"status":"ok"}`
  - `https://app.nt524.io.vn/healthz` qua AWS gateway: `{"status":"ok"}`
  - `http://app.nt524.io.vn/` tra `301` sang HTTPS.
  - `https://app.nt524.io.vn/` tra `302` sang Cognito Hosted UI.
  - Ep DNS sang OpenStack gateway, `https://app.nt524.io.vn/` cung tra `302` sang Cognito Hosted UI.
  - `oauth2-proxy` va `nginx` active tren ca hai gateway.
- Da fix loi `502 Bad Gateway` sau khi login Cognito:
  - Nguyen nhan: Nginx default proxy buffer qua nho voi header/cookie lon tu oauth2-proxy tren `/oauth2/callback`.
  - Da tang `proxy_buffer_size`, `proxy_buffers`, `proxy_busy_buffers_size` cho `/oauth2/` va `/oauth2/auth`.
  - Da tang `large_client_header_buffers` trong server HTTP/HTTPS.
  - Da deploy lai `ansible/gateway.yml` thanh cong tren ca hai gateway.
- Luu y hien tai:
  - Gateway dang dung self-signed TLS cert cho lab HTTPS, nen browser se can accept warning khi truy cap lan dau.
  - Buoc tot hon tiep theo la thay self-signed cert bang Let's Encrypt/public TLS cert va copy cung cert/key sang ca hai gateway.

## Cap nhat 2026-05-27 - Test Route 53 failover sau Cognito

- Da test failover/failback voi domain that `app.nt524.io.vn` sau khi them Cognito/oauth2-proxy.
- Trang thai truoc test:
  - AWS gateway `http://122.248.227.98/healthz`: `{"status":"ok"}`
  - OpenStack gateway `http://172.10.10.208/healthz`: `{"status":"ok"}`
  - Route 53 authoritative DNS: `app.nt524.io.vn -> 122.248.227.98`
  - Route 53 AWS health check: `Success: HTTP Status Code 200, OK`
- Da stop tam Nginx tren `aws-gateway` de gia lap AWS gateway fail.
- Ket qua failover:
  - AWS gateway HTTP chuyen sang connection refused.
  - OpenStack gateway van `200`.
  - Route 53 authoritative DNS chuyen sang OpenStack: `app.nt524.io.vn -> 172.10.10.208`.
- Da start lai Nginx tren `aws-gateway`.
- Ket qua failback:
  - AWS gateway `/healthz` hoi phuc `200`.
  - Route 53 authoritative DNS quay lai AWS: `app.nt524.io.vn -> 122.248.227.98`.
  - Route 53 AWS health check cuoi test: `8/8 Success: HTTP Status Code 200, OK`.
  - AWS gateway va OpenStack gateway cuoi test deu `{"status":"ok"}`.
- Luu y:
  - Trong failover, browser/public resolver co the giu cache DNS toi TTL hien tai cua record (`30s`) hoac lau hon tuy resolver.
  - Health check dang kiem tra HTTP `/healthz`, khong di qua Cognito login. Day la dung cho DNS failover vi auth redirect khong nen lam health check fail.

## Cap nhat 2026-05-27

- Da tao Route 53 failover bang Terraform AWS.
  - File moi: `terraform/aws/route53.tf`
  - Bat trong `terraform/aws/terraform.tfvars`:
    - `route53_failover_enabled = true`
    - `route53_create_hosted_zone = true`
    - `route53_zone_name = "hybrid-lab.test"`
    - `route53_record_name = "app"`
    - `route53_secondary_gateway_ip = "172.10.10.208"`
  - Terraform da tao:
    - Public hosted zone: `hybrid-lab.test`
    - Failover FQDN: `app.hybrid-lab.test`
    - Primary A record: AWS gateway `122.248.227.98`
    - Secondary A record: OpenStack gateway `172.10.10.208`
    - AWS primary health check: `f8c7d0d4-b6fc-4311-b5bd-2c5fe44e3ed9`
  - Route 53 authoritative nameservers:
    - `ns-1108.awsdns-10.org`
    - `ns-1689.awsdns-19.co.uk`
    - `ns-330.awsdns-41.com`
    - `ns-806.awsdns-36.net`
- Luu y ve domain lab:
  - `hybrid-lab.test` chi dung de test tren authoritative nameserver bang `dig @ns-1108.awsdns-10.org app.hybrid-lab.test`.
  - Neu muon user truy cap binh thuong bang browser/public DNS, can dung domain that da mua/delegate nameserver ve Route 53.
- Da test Route 53 failover:
  - Khi AWS gateway healthy:
    - Route 53 health check: `Success: HTTP Status Code 200, OK`
    - `dig +short @ns-1108.awsdns-10.org app.hybrid-lab.test A`: `122.248.227.98`
  - Stop tam nginx tren AWS gateway de test failover:
    - Route 53 health check chuyen sang failure.
    - DNS chuyen sang OpenStack secondary: `172.10.10.208`
  - Start lai nginx AWS gateway de test failback:
    - Ban dau AWS van unhealthy vi AWS app khong ket noi duoc DB.
    - Nguyen nhan: public WAN IP cua OpenStack/laptop da doi tu `171.248.116.219` sang `115.72.50.156`, AWS VPN security group van allow IP cu nen WireGuard khong handshake.
    - Da cap nhat `openstack_vpn_public_cidr = "115.72.50.156/32"` trong `terraform/aws/terraform.tfvars`.
    - Da `terraform apply` AWS: chi update in-place `vpn_sg` UDP `51820`.
    - Restart `wg-quick@wg0` tren OpenStack VPN; WireGuard handshake hoi phuc.
    - Restart container AWS app `hybrid-auth-app` vi app bi ket sau khi DB mat ket noi.
    - Route 53 health check hoi phuc `16/16 Success`.
    - DNS failback ve AWS primary: `122.248.227.98`.
- Trang thai hien tai sau khi sua:
  - AWS gateway `http://122.248.227.98/healthz`: `{"status":"ok"}`
  - OpenStack gateway `http://172.10.10.208/healthz`: `{"status":"ok"}`
  - AWS WAF local health: `{"status":"ok"}`
  - AWS WAF -> AWS app private health: `{"status":"ok"}`
  - AWS VPN -> PostgreSQL OpenStack `10.0.1.94:5432`: OK
  - OpenStack VPN -> AWS WireGuard IP `10.200.0.1`: ping OK
  - Current Route 53 answer via authoritative NS: `122.248.227.98`

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
  - AWS WAF public/private IP luc dau: `13.229.165.24` / `172.31.4.221`
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
  - AWS WAF public luc dau `http://13.229.165.24/healthz`: `{"status":"ok"}`; sau khi them AWS gateway thi public EIP nay da bi remove.
  - AWS WAF local -> AWS app private: `{"status":"ok"}`
  - OpenStack WAF local -> OpenStack app private: `{"status":"ok"}`
  - SQLi test qua AWS WAF: HTTP `403`
  - SQLi test qua OpenStack WAF: HTTP `403`
- Da lam gateway entrypoint truoc Cognito/Route53:
  - Thu tu chon: gateway truoc -> Route 53 failover -> Cognito/oauth2-proxy.
  - Ly do: Route 53 can public endpoint on dinh; Cognito callback nen tro ve gateway DNS, khong tro truc tiep WAF.
- OpenStack gateway:
  - Da thu tao VM `openstack-gateway` rieng nhung OpenStack AIO bi `NoValidHost` do thieu capacity cho VM thu 5.
  - Tam dung `vpn-gateway` lam public gateway OpenStack vi da co floating IP va nam tren WAF transit net.
  - Public endpoint: `http://172.10.10.208`.
  - Gateway proxy den OpenStack WAF `10.0.2.10:80`.
- AWS gateway:
  - Terraform AWS da tao `aws-gateway-node`.
  - Public endpoint: `http://122.248.227.98`.
  - Gateway proxy den AWS WAF private `172.31.4.221:80`.
  - AWS WAF public EIP cu `13.229.165.24` da bi remove; curl toi IP cu timeout.
  - SSH toi `aws-waf` hien di qua `aws-gateway`.
- Da sua route/NAT cho DB centralized:
  - `openstack-vpn` route `10.0.1.0/24` qua WAF transit `10.0.2.10`.
  - `openstack-waf` bat ip_forward va NAT/MASQUERADE traffic tu transit/VPN/AWS sang app/db net.
  - Them systemd service persist route/NAT:
    - `openstack-app-route.service` tren OpenStack VPN.
    - `openstack-waf-routing.service` tren OpenStack WAF.
- Da sua Ansible de phu hop moi truong OpenStack han che DNS/internet:
  - `nginx_waf` skip Docker/ECR/CRS download neu da co san tren host.
  - `filebeat_agent` skip Elastic repo/key/install neu Filebeat da co san.
  - Proxy SSH qua gateway them `StrictHostKeyChecking=no` cho target recreated sau Terraform destroy/apply.
- Kiem tra sau gateway:
  - `ansible-playbook ansible/network_vpn.yml --syntax-check`: OK.
  - `ansible-playbook ansible/waf.yml --syntax-check`: OK.
  - `ansible-playbook ansible/network_vpn.yml`: OK.
  - `ansible-playbook ansible/waf.yml --limit openstack-waf`: OK.
  - OpenStack gateway `http://172.10.10.208/healthz`: `{"status":"ok"}`.
  - AWS gateway `http://122.248.227.98/healthz`: `{"status":"ok"}`.
  - SQLi test qua OpenStack gateway: HTTP `403`.
  - SQLi test qua AWS gateway: HTTP `403`.
  - `openstack-vpn -> PostgreSQL 10.0.1.94:5432`: OK.
  - `aws-vpn -> PostgreSQL 10.0.1.94:5432`: OK.
  - `aws-app -> PostgreSQL 10.0.1.94:5432`: OK.
  - `aws-app` local health: `{"status":"ok"}`.

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

1. Thay self-signed gateway TLS cert bang Let's Encrypt/public TLS cert.
2. Delegate nameserver cua `nt524.io.vn` sang 4 Route 53 nameserver moi de public DNS tra `app.nt524.io.vn`.
3. Bo sung health endpoint cho gateway/controller neu can tach khoi `/healthz` cua app.
4. Giam rui ro WAN IP thay doi:
   - cap nhat lai `openstack_vpn_public_cidr` moi khi public IP laptop/OpenStack AIO doi,
   - hoac mo WireGuard UDP `51820` rong hon trong lab,
   - hoac dung public IP/static NAT that cho OpenStack side.

## Ghi chu quan trong

- Hien tai AWS app va OpenStack app deu dung chung PostgreSQL centralized tren OpenStack.
- AWS app public HTTP bi chan; duong user hop le hien tai la qua AWS gateway `122.248.227.98`.
- AWS WAF khong con public EIP; chi nhan traffic tu AWS gateway/private network.
- OpenStack public entrypoint hien tai la `vpn-gateway` kiem gateway proxy `172.10.10.208`.
- Route 53 failover hien tai da dung hosted zone `nt524.io.vn`; authoritative DNS da tra dung `app.nt524.io.vn`, public DNS con can delegate nameserver/cho cache het han.
- Neu public WAN IP cua laptop/OpenStack AIO doi, AWS WireGuard SG se chan tunnel cho den khi cap nhat `openstack_vpn_public_cidr`.
- Neu recreate Terraform, cap nhat lai `hosts.yml` theo output moi.
