output "vpn_gateway_public_ip" {
  value = openstack_compute_floatingip_associate_v2.fip_assoc.floating_ip
}

output "app_node_private_ip" {
  value = openstack_compute_instance_v2.app_node.network[0].fixed_ip_v4
}

output "waf_node_private_ip" {
  value = openstack_compute_instance_v2.waf_node.network[0].fixed_ip_v4
}
