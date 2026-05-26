variable "app_subnet_cidr" {
  description = "CIDR range of the app node private network"
  type        = string
}

variable "waf_subnet_cidr" {
  description = "CIDR range of the VPN-to-WAF transit network"
  type        = string
}

variable "db_allowed_cidrs" {
  description = "CIDR ranges allowed to reach PostgreSQL on the DB node"
  type        = list(string)
}
