locals {
  cognito_gateway_base_url = "https://${local.route53_record_fqdn}"
  cognito_callback_url     = "${local.cognito_gateway_base_url}/oauth2/callback"
  cognito_logout_url       = "${local.cognito_gateway_base_url}/"
  cognito_issuer_url       = var.cognito_enabled ? "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.hybrid_auth[0].id}" : null
}

resource "aws_cognito_user_pool" "hybrid_auth" {
  count = var.cognito_enabled ? 1 : 0

  name = var.cognito_user_pool_name

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  mfa_configuration        = "OFF"

  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = false
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  schema {
    attribute_data_type = "String"
    mutable             = true
    name                = "email"
    required            = true

    string_attribute_constraints {
      min_length = 1
      max_length = 2048
    }
  }

  tags = {
    Name        = var.cognito_user_pool_name
    Environment = "Production"
  }
}

resource "aws_cognito_user_pool_client" "gateway" {
  count = var.cognito_enabled ? 1 : 0

  name         = var.cognito_app_client_name
  user_pool_id = aws_cognito_user_pool.hybrid_auth[0].id

  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  callback_urls                        = [local.cognito_callback_url]
  logout_urls                          = [local.cognito_logout_url]
  supported_identity_providers         = ["COGNITO"]
  prevent_user_existence_errors        = "ENABLED"

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
}

resource "aws_cognito_user_pool_domain" "hosted_ui" {
  count = var.cognito_enabled ? 1 : 0

  domain       = var.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.hybrid_auth[0].id
}
