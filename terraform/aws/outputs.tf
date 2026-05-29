output "vpn_public_ip" {
  value = module.compute.vpn_public_ip
}

output "gateway_public_ip" {
  value = module.compute.gateway_public_ip
}

output "waf_private_ip" {
  value = module.compute.waf_private_ip
}

output "app_public_ip" {
  value = module.compute.app_public_ip
}

output "app_private_ip" {
  value = module.compute.app_private_ip
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

output "ecr_repository_url" {
  value       = aws_ecr_repository.waf.repository_url
  description = "The URL of the ECR repository for the WAF image"
}

output "route53_failover_fqdn" {
  value       = var.route53_failover_enabled ? local.route53_record_fqdn : null
  description = "Failover DNS name for the app gateway."
}

output "route53_zone_name_servers" {
  value       = var.route53_failover_enabled && var.route53_create_hosted_zone ? aws_route53_zone.failover[0].name_servers : []
  description = "Authoritative Route 53 name servers for the created lab hosted zone."
}

output "route53_aws_gateway_health_check_id" {
  value       = var.route53_failover_enabled ? aws_route53_health_check.aws_gateway[0].id : null
  description = "Route 53 health check ID for the AWS primary gateway."
}

output "cognito_user_pool_id" {
  value       = var.cognito_enabled ? aws_cognito_user_pool.hybrid_auth[0].id : null
  description = "Cognito user pool ID for gateway authentication."
}

output "cognito_user_pool_client_id" {
  value       = var.cognito_enabled ? aws_cognito_user_pool_client.gateway[0].id : null
  description = "Cognito app client ID used by oauth2-proxy."
}

output "cognito_user_pool_client_secret" {
  value       = var.cognito_enabled ? aws_cognito_user_pool_client.gateway[0].client_secret : null
  description = "Cognito app client secret used by oauth2-proxy."
  sensitive   = true
}

output "cognito_issuer_url" {
  value       = local.cognito_issuer_url
  description = "OIDC issuer URL for oauth2-proxy."
}

output "cognito_hosted_ui_base_url" {
  value       = var.cognito_enabled ? "https://${aws_cognito_user_pool_domain.hosted_ui[0].domain}.auth.${var.aws_region}.amazoncognito.com" : null
  description = "Cognito hosted UI base URL."
}
