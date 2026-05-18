# SIEM Hybrid Network/VPN Ansible

This Ansible layer configures the current deployment milestones for the topology.

Deferred roles:

- AWS WAF node: ModSecurity
- MLflow/FastAPI/model integration

## Order

1. Apply OpenStack Terraform and record `vpn_public_ip` and `app_node_ip`.
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

7. Deploy the App node:

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

## Expected Tunnel

- AWS VPN WireGuard IP: `10.200.0.1`
- OpenStack VPN WireGuard IP: `10.200.0.2`
- AWS VPC CIDR: `172.31.0.0/16`
- OpenStack App CIDR: `10.0.1.0/24`

The OpenStack VPN gateway applies NAT from `172.31.0.0/16` to `10.0.1.0/24` during testing, so the app node can accept traffic via the VPN gateway path without tightening security groups yet.

## Current App/WAF Layer

- App node runs OWASP Juice Shop in Docker: `bkimminich/juice-shop`, exposed on port `80`.
- WAF node runs Nginx as a reverse proxy to `http://10.0.1.39:80`.
- Logstash runs on the OpenStack VPN node and writes to Elasticsearch on the laptop at `172.10.10.1:9200`.
- Filebeat is installed on both App and WAF nodes.
- Filebeat is configured to send to `{{ logstash_host }}:{{ logstash_port }}` from `group_vars/all.yml`; currently this resolves to `10.0.1.254:5044`.
- ModSecurity is intentionally not installed yet.
