terraform {
  required_providers {
    openstack = {
      source = "terraform-provider-openstack/openstack"
    }
  }
}
resource "openstack_networking_secgroup_v2" "app_sg" {
  name        = "app_node_sg"
  description = "Security group for Web App Node"
}

resource "openstack_networking_secgroup_rule_v2" "app_ssh" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.app_sg.id
}

resource "openstack_networking_secgroup_rule_v2" "app_http" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 80
  port_range_max    = 80
  remote_group_id   = openstack_networking_secgroup_v2.vpn_sg.id
  security_group_id = openstack_networking_secgroup_v2.app_sg.id
}

resource "openstack_networking_secgroup_rule_v2" "app_https" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 443
  port_range_max    = 443
  remote_group_id   = openstack_networking_secgroup_v2.vpn_sg.id
  security_group_id = openstack_networking_secgroup_v2.app_sg.id
}

resource "openstack_networking_secgroup_v2" "vpn_sg" {
  name        = "vpn_sg"
  description = "Security group for VPN Node"
}

resource "openstack_networking_secgroup_rule_v2" "vpn_ssh" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.vpn_sg.id
}

resource "openstack_networking_secgroup_rule_v2" "vpn_wg" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "udp"
  port_range_min    = 51820
  port_range_max    = 51820
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.vpn_sg.id
}


resource "openstack_networking_secgroup_rule_v2" "vpn_allow_app_net" {
  direction         = "ingress"
  ethertype         = "IPv4"
  remote_ip_prefix  = var.app_subnet_cidr
  security_group_id = openstack_networking_secgroup_v2.vpn_sg.id
}

resource "openstack_networking_secgroup_rule_v2" "vpn_icmp" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "icmp"
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.vpn_sg.id
}
