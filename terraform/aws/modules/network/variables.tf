variable "vpc_id" {
  type        = string
  description = "Existing AWS VPC ID for the SIEM deployment."
}

variable "subnet_id" {
  type        = string
  description = "Existing public subnet ID for the WAF and VPN nodes."
}

variable "route_table_id" {
  type        = string
  description = "Existing route table ID associated with the public subnet."
}
