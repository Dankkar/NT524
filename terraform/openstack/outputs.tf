output "vpn_public_ip" {
  value       = module.compute.vpn_gateway_public_ip
  description = "Floating IP of the VPN Gateway"
}

output "app_node_ip" {
  value       = module.compute.app_node_private_ip
  description = "Private IP of the App Node"
}
