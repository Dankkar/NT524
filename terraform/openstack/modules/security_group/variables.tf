variable "app_subnet_cidr" {
  description = "CIDR range of the app node private network"
  type        = string
}

variable "waf_subnet_cidr" {
  description = "CIDR range of the VPN-to-WAF transit network"
  type        = string
}
