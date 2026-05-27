variable "subnet_id" {
  type = string
}

variable "waf_sg_id" {
  type = string
}

variable "vpn_sg_id" {
  type = string
}

variable "app_sg_id" {
  type = string
}

variable "gateway_sg_id" {
  type = string
}

variable "public_key_path" {
  type = string
}

variable "keypair_name" {
  type = string
}

variable "instance_type" {
  type = string
}

variable "vpn_node_name" {
  type = string
}

variable "waf_node_name" {
  type = string
}

variable "app_node_name" {
  type = string
}

variable "gateway_node_name" {
  type = string
}

variable "waf_iam_instance_profile" {
  type    = string
  default = ""
}
