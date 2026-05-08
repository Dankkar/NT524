output "private_network_id" {
  value = openstack_networking_network_v2.private_net.id
}

output "private_subnet_id" {
  value = openstack_networking_subnet_v2.private_subnet.id
}

output "vpn_floating_ip" {
  value = openstack_networking_floatingip_v2.vpn_fip.address
}

output "app_network_id" {
  value = openstack_networking_network_v2.app_private_net.id
}

output "app_subnet_id" {
  value = openstack_networking_subnet_v2.app_private_subnet.id
}
