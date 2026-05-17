variable "vpc_id" {
  type        = string
  description = "VPC ID where the security groups will be created"
}

variable "vpc_cidr_block" {
  type        = string
  description = "CIDR block of the existing AWS VPC."
}

variable "openstack_vpn_public_cidr" {
  type        = string
  description = "CIDR allowed to connect to WireGuard on the AWS VPN node."
}
