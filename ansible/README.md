# SIEM Hybrid Network/VPN Ansible

This Ansible layer configures the current deployment milestones for the topology.

Deferred roles:

- AWS WAF node: ModSecurity
- MLflow/FastAPI/model integration

## Order

1. Apply OpenStack Terraform and record `vpn_public_ip`, `waf_transit_ip`, `app_node_ip`, and `db_node_ip`.
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
- OpenStack WAF transit CIDR: `10.0.2.0/24`
- OpenStack App/DB CIDR: `10.0.1.0/24`

The OpenStack VPN gateway routes traffic to the WAF transit network. App and DB nodes sit behind the WAF on the app private network, so inbound app traffic should pass through VPN -> WAF -> App.

## Current App/WAF Layer

- DB node runs PostgreSQL in Docker with persistent data under `/opt/hybrid-auth/postgres/data`.
- App node runs the lightweight Flask auth app in Docker, exposed on port `80`, using PostgreSQL through `DATABASE_URL`.
- WAF node runs Nginx/ModSecurity as a reverse proxy to the app private IP.
- Logstash runs on the OpenStack VPN node and writes to Elasticsearch on the laptop at `172.10.10.1:9200`.
- Filebeat is installed on both App and WAF nodes.
- Filebeat is configured to send to `{{ logstash_host }}:{{ logstash_port }}` from `group_vars/all.yml`; currently this resolves to `10.0.1.254:5044`.
