terraform {
  required_providers {
    openstack = {
      source = "terraform-provider-openstack/openstack"
    }
  }
}
resource "openstack_networking_network_v2" "private_net" {
  name           = "vpn_private_net"
  admin_state_up = "true"
}

resource "openstack_networking_subnet_v2" "private_subnet" {
  name       = "vpn_private_subnet"
  network_id = openstack_networking_network_v2.private_net.id
  cidr       = "10.0.0.0/24"
  ip_version = 4
}

# Mạng private riêng biệt cho App Node (Không nối ra Router)
resource "openstack_networking_network_v2" "app_private_net" {
  name           = "app_private_net"
  admin_state_up = "true"
}

resource "openstack_networking_subnet_v2" "app_private_subnet" {
  name       = "app_private_subnet"
  network_id = openstack_networking_network_v2.app_private_net.id
  cidr       = "10.0.1.0/24"
  ip_version = 4
  no_gateway = true
}

# router private to public
resource "openstack_networking_router_v2" "router" {
  name                = "internet_gateway_router"
  admin_state_up      = "true"
  external_network_id = var.external_network_id
}

resource "openstack_networking_router_interface_v2" "router_iface" {
  router_id = openstack_networking_router_v2.router.id
  subnet_id = openstack_networking_subnet_v2.private_subnet.id
}

resource "openstack_networking_floatingip_v2" "vpn_fip" {
  pool = "public-net"
}
