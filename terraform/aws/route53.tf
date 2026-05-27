locals {
  route53_zone_name   = trimsuffix(var.route53_zone_name, ".")
  route53_record_name = trimsuffix(var.route53_record_name, ".")
  route53_record_fqdn = local.route53_record_name == "" ? local.route53_zone_name : "${local.route53_record_name}.${local.route53_zone_name}"
  route53_zone_id     = var.route53_create_hosted_zone ? aws_route53_zone.failover[0].zone_id : var.route53_hosted_zone_id
}

resource "aws_route53_zone" "failover" {
  count = var.route53_failover_enabled && var.route53_create_hosted_zone ? 1 : 0

  name = local.route53_zone_name
}

resource "aws_route53_health_check" "aws_gateway" {
  count = var.route53_failover_enabled ? 1 : 0

  ip_address        = module.compute.gateway_public_ip
  type              = "HTTP"
  port              = 80
  resource_path     = var.route53_health_check_path
  failure_threshold = 3
  request_interval  = 30

  tags = {
    Name = "aws-gateway-primary-health"
  }
}

resource "aws_route53_record" "aws_gateway_primary" {
  count = var.route53_failover_enabled ? 1 : 0

  zone_id = local.route53_zone_id
  name    = local.route53_record_fqdn
  type    = "A"
  ttl     = 30
  records = [module.compute.gateway_public_ip]

  set_identifier  = "aws-primary"
  health_check_id = aws_route53_health_check.aws_gateway[0].id

  failover_routing_policy {
    type = "PRIMARY"
  }

  lifecycle {
    precondition {
      condition     = var.route53_create_hosted_zone || var.route53_hosted_zone_id != ""
      error_message = "route53_hosted_zone_id is required when route53_create_hosted_zone is false."
    }
  }
}

resource "aws_route53_record" "openstack_gateway_secondary" {
  count = var.route53_failover_enabled ? 1 : 0

  zone_id = local.route53_zone_id
  name    = local.route53_record_fqdn
  type    = "A"
  ttl     = 30
  records = [var.route53_secondary_gateway_ip]

  set_identifier = "openstack-secondary"

  failover_routing_policy {
    type = "SECONDARY"
  }
}
