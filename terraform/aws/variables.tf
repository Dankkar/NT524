variable "aws_region" {
  type    = string
  default = "ap-southeast-1"
}

variable "vpc_id" {
  type        = string
  description = "Existing AWS VPC ID."
  default     = "vpc-03b81e1c8a2892dbc"
}

variable "subnet_id" {
  type        = string
  description = "Existing AWS subnet ID in ap-southeast-1a for WAF and VPN nodes."
  default     = "subnet-02126da524c71473c"
}

variable "route_table_id" {
  type        = string
  description = "Existing AWS route table ID associated with the selected subnet."
  default     = "rtb-01c9191c5ba9d25ea"
}

variable "openstack_app_cidr" {
  type        = string
  description = "OpenStack App Node network routed through the AWS VPN gateway."
  default     = "10.0.1.0/24"
}

variable "openstack_vpn_public_cidr" {
  type        = string
  description = "OpenStack VPN public floating IP allowed to access AWS WireGuard, in CIDR form such as x.x.x.x/32."
}

variable "public_key_path" {
  type    = string
  default = "~/.ssh/aws_vpn_key.pub"
}
