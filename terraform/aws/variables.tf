variable "aws_region" {
  type        = string
  description = "AWS region used for the SIEM AWS nodes."
  default     = "ap-southeast-1"
}

variable "aws_profile" {
  type        = string
  description = "Local AWS CLI profile used to manage the existing AWS account. Leave empty to use the default credential chain."
  default     = ""
}

variable "terraform_state_backend_enabled" {
  type        = bool
  description = "Create S3 and DynamoDB resources used as a shared Terraform remote state backend."
  default     = true
}

variable "terraform_state_bucket_name" {
  type        = string
  description = "S3 bucket name for shared Terraform state. Leave empty to derive nt524-terraform-state-<account>-<region>."
  default     = ""
}

variable "terraform_lock_table_name" {
  type        = string
  description = "DynamoDB table name for Terraform state locking."
  default     = "nt524-terraform-locks"
}

variable "vpc_id" {
  type        = string
  description = "Existing AWS VPC ID in the selected region, for example vpc-0123456789abcdef0."

  validation {
    condition     = can(regex("^vpc-[0-9a-f]+$", var.vpc_id))
    error_message = "vpc_id must look like an AWS VPC ID, for example vpc-0123456789abcdef0."
  }
}

variable "subnet_id" {
  type        = string
  description = "Existing public subnet ID for the WAF and VPN nodes, for example subnet-0123456789abcdef0."

  validation {
    condition     = can(regex("^subnet-[0-9a-f]+$", var.subnet_id))
    error_message = "subnet_id must look like an AWS subnet ID, for example subnet-0123456789abcdef0."
  }
}

variable "route_table_id" {
  type        = string
  description = "Existing route table ID associated with the selected public subnet, for example rtb-0123456789abcdef0."

  validation {
    condition     = can(regex("^rtb-[0-9a-f]+$", var.route_table_id))
    error_message = "route_table_id must look like an AWS route table ID, for example rtb-0123456789abcdef0."
  }
}

variable "openstack_app_cidr" {
  type        = string
  description = "OpenStack App Node network routed through the AWS VPN gateway."
  default     = "10.0.1.0/24"
}

variable "openstack_waf_transit_cidr" {
  type        = string
  description = "OpenStack WAF/VPN transit network routed through the AWS VPN gateway for Logstash and WAF transit access."
  default     = "10.0.2.0/24"
}

variable "openstack_vpn_public_cidr" {
  type        = string
  description = "Real public source CIDR allowed to access AWS WireGuard. For laptop OpenStack AIO, this is the WAN/NAT public IP as x.x.x.x/32, not the 172.10.10.x floating IP."

  validation {
    condition     = can(cidrhost(var.openstack_vpn_public_cidr, 0))
    error_message = "openstack_vpn_public_cidr must be a valid CIDR such as 203.0.113.10/32."
  }
}

variable "public_key_path" {
  type        = string
  description = "Path to the SSH public key imported as the AWS EC2 key pair."
  default     = "~/.ssh/aws_vpn_key.pub"
}

variable "keypair_name" {
  type        = string
  description = "Name of the AWS EC2 Keypair"
  default     = "aws_vpn_key"
}

variable "instance_type" {
  type        = string
  description = "EC2 Instance type for WAF and VPN nodes"
  default     = "t3.micro"
}

variable "db_instance_type" {
  type        = string
  description = "EC2 instance type for the dedicated AWS PostgreSQL DB node."
  default     = "t2.nano"
}

variable "vpn_node_name" {
  type        = string
  description = "Name tag for the AWS VPN node"
  default     = "aws-vpn-gateway"
}

variable "waf_node_name" {
  type        = string
  description = "Name tag for the AWS WAF node"
  default     = "aws-waf-node"
}

variable "app_node_name" {
  type        = string
  description = "Name tag for the AWS app node"
  default     = "aws-app-node"
}

variable "db_node_name" {
  type        = string
  description = "Name tag for the AWS PostgreSQL primary DB node"
  default     = "aws-db-node"
}

variable "gateway_node_name" {
  type        = string
  description = "Name tag for the AWS public gateway node"
  default     = "aws-gateway-node"
}

variable "route53_failover_enabled" {
  type        = bool
  description = "Create Route 53 active/passive failover records for the public gateways."
  default     = false
}

variable "route53_create_hosted_zone" {
  type        = bool
  description = "Create a lab public hosted zone. Set false when using an existing hosted zone ID."
  default     = true
}

variable "route53_hosted_zone_id" {
  type        = string
  description = "Existing Route 53 hosted zone ID. Required when route53_create_hosted_zone is false."
  default     = ""
}

variable "route53_zone_name" {
  type        = string
  description = "Route 53 zone name for failover DNS."
  default     = "hybrid-lab.test"
}

variable "route53_record_name" {
  type        = string
  description = "Record name under route53_zone_name for the app entrypoint."
  default     = "app"
}

variable "route53_secondary_gateway_ip" {
  type        = string
  description = "OpenStack gateway IP used as the Route 53 secondary failover target."
  default     = "172.10.10.208"
}

variable "route53_health_check_path" {
  type        = string
  description = "HTTP path Route 53 checks on the AWS gateway primary target."
  default     = "/healthz"
}

variable "cognito_enabled" {
  type        = bool
  description = "Create an Amazon Cognito user pool and hosted UI app client for gateway authentication."
  default     = true
}

variable "cognito_user_pool_name" {
  type        = string
  description = "Name of the Cognito user pool used by the hybrid auth gateway."
  default     = "hybrid-auth-users"
}

variable "cognito_app_client_name" {
  type        = string
  description = "Name of the Cognito app client used by oauth2-proxy."
  default     = "hybrid-auth-gateway"
}

variable "cognito_domain_prefix" {
  type        = string
  description = "Globally unique Cognito hosted UI domain prefix in the selected AWS region."
  default     = "nt524-hybrid-auth-211116632423"
}
