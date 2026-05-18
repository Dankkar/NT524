variable "network_id" {}
variable "subnet_id" {}
variable "app_sg_id" {}
variable "vpn_sg_id" {}
variable "floating_ip" {}
variable "app_network_id" {}
variable "app_subnet_id" {}

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

variable "vpn_node_name" {
  type = string
}

variable "vpn_app_ip" {
  type = string
}
