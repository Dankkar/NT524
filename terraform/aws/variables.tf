variable "aws_region" {
  type        = string
  description = "AWS region used for the SIEM AWS nodes."
  default     = "ap-southeast-1"
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

variable "github_repository" {
  type        = string
  description = "GitHub repository path (e.g. your-username/your-repo-name) allowed to assume the ECR push role"
  default     = "Dankkar/NT524"
}
