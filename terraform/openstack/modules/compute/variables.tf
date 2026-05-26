variable "network_id" {}
variable "subnet_id" {}
variable "waf_network_id" {}
variable "waf_subnet_id" {}
variable "vpn_sg_id" {}
variable "waf_sg_id" {}
variable "app_sg_name" {}
variable "vpn_sg_name" {}
variable "waf_sg_name" {}
variable "db_sg_name" {}
variable "floating_ip" {}
variable "app_network_id" {}
variable "app_subnet_id" {}
variable "app_subnet_cidr" {}

# New configuration variables
variable "keypair_name" {
  type = string
}

variable "public_key_path" {
  type = string
}

variable "image_name" {
  type = string
}

variable "flavor_name" {
  type = string
}

variable "app_node_name" {
  type = string
}

variable "waf_node_name" {
  type = string
}

variable "db_node_name" {
  type = string
}

variable "vpn_node_name" {
  type = string
}

variable "vpn_app_ip" {
  type = string
}

variable "vpn_waf_ip" {
  type = string
}

variable "waf_transit_ip" {
  type = string
}
