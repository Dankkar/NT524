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

output "github_actions_role_arn" {
  value       = aws_iam_role.github_actions.arn
  description = "The ARN of the IAM role for GitHub Actions OIDC"
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.waf.repository_url
  description = "The URL of the ECR repository for the WAF image"
}
