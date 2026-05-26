output "vpn_public_ip" {
  value       = module.compute.vpn_gateway_public_ip
  description = "Floating IP of the VPN Gateway"
}

output "app_node_ip" {
  value       = module.compute.app_node_private_ip
  description = "Private IP of the App Node"
}

output "waf_node_ip" {
  value       = module.compute.waf_node_private_ip
  description = "Private IP of the OpenStack WAF Node"
}

output "db_node_ip" {
  value       = module.compute.db_node_private_ip
  description = "Private IP of the OpenStack centralized Database Node"
}
