# SIEM Hybrid Network/VPN Ansible

This Ansible layer configures only the network/VPN milestone for the deployment topology.

Deferred roles:

- AWS WAF node: Nginx, ModSecurity, Filebeat
- OpenStack App node: Juice Shop/WebServer, Filebeat

## Order

1. Apply OpenStack Terraform and record `vpn_public_ip` and `app_node_ip`.
2. Apply AWS Terraform with `openstack_vpn_public_cidr=<OPENSTACK_VPN_PUBLIC_IP>/32`.
3. Replace the `CHANGE_ME_*` values in `inventories/production/hosts.yml`.
4. Run the VPN playbook:

```bash
ansible-playbook network_vpn.yml
```

## Expected Tunnel

- AWS VPN WireGuard IP: `10.200.0.1`
- OpenStack VPN WireGuard IP: `10.200.0.2`
- AWS VPC CIDR: `172.31.0.0/16`
- OpenStack App CIDR: `10.0.1.0/24`

The OpenStack VPN gateway applies NAT from `172.31.0.0/16` to `10.0.1.0/24` during testing, so the app node can accept traffic via the VPN gateway path without tightening security groups yet.
