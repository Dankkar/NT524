output "vpn_public_ip" {
  value = aws_eip.vpn_eip.public_ip
}

output "gateway_public_ip" {
  value = aws_eip.gateway_eip.public_ip
}

output "waf_private_ip" {
  value = aws_instance.waf_node.private_ip
}

output "app_public_ip" {
  value = aws_instance.app_node.public_ip
}

output "app_private_ip" {
  value = aws_instance.app_node.private_ip
}

output "db_private_ip" {
  value = aws_instance.db_node.private_ip
}

output "db_instance_id" {
  value = aws_instance.db_node.id
}

output "vpn_private_ip" {
  value = aws_instance.vpn_gateway.private_ip
}

output "vpn_instance_id" {
  value = aws_instance.vpn_gateway.id
}

output "vpn_network_interface_id" {
  value = aws_instance.vpn_gateway.primary_network_interface_id
}
