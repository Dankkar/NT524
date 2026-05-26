output "waf_sg_id" {
  value = aws_security_group.waf_sg.id
}

output "vpn_sg_id" {
  value = aws_security_group.vpn_sg.id
}

output "app_sg_id" {
  value = aws_security_group.app_sg.id
}
