output "waf_public_ip" {
  value = module.compute.waf_public_ip
}

output "vpn_public_ip" {
  value = module.compute.vpn_public_ip
}

output "waf_private_ip" {
  value = module.compute.waf_private_ip
}

output "vpn_private_ip" {
  value = module.compute.vpn_private_ip
}

output "vpn_instance_id" {
  value = module.compute.vpn_instance_id
}

output "vpn_network_interface_id" {
  value = module.compute.vpn_network_interface_id
}
