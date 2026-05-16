output "waf_public_ip" {
  value = aws_eip.waf_eip.public_ip
}

output "vpn_public_ip" {
  value = aws_eip.vpn_eip.public_ip
}
