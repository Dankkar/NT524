variable "aws_region" {
  type    = string
  default = "ap-southeast-1"
}

variable "public_key_path" {
  type    = string
  default = "~/.ssh/aws_vpn_key.pub"
}
