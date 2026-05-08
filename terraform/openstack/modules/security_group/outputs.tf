output "app_sg_id" {
  value = openstack_networking_secgroup_v2.app_sg.id
}

output "vpn_sg_id" {
  value = openstack_networking_secgroup_v2.vpn_sg.id
}
