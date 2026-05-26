output "app_sg_id" {
  value = openstack_networking_secgroup_v2.app_sg.id
}

output "app_sg_name" {
  value = openstack_networking_secgroup_v2.app_sg.name
}

output "vpn_sg_id" {
  value = openstack_networking_secgroup_v2.vpn_sg.id
}

output "vpn_sg_name" {
  value = openstack_networking_secgroup_v2.vpn_sg.name
}

output "waf_sg_id" {
  value = openstack_networking_secgroup_v2.waf_sg.id
}

output "waf_sg_name" {
  value = openstack_networking_secgroup_v2.waf_sg.name
}

output "db_sg_name" {
  value = openstack_networking_secgroup_v2.db_sg.name
}
