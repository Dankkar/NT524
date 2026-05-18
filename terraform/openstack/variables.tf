variable "external_network_id" {
  description = "ID of the external/public network"
  type        = string
}

variable "floating_ip_pool" {
  description = "Name of the floating IP pool (e.g. public-net, public1, external)"
  type        = string
  default     = "public-net"
}

variable "keypair_name" {
  description = "Name of the OpenStack SSH Keypair"
  type        = string
  default     = "vpn_key"
}

variable "public_key_path" {
  description = "Path to the SSH public key file"
  type        = string
  default     = "~/.ssh/vpn_key.pub"
}

variable "image_name" {
  description = "Image name for both virtual machines"
  type        = string
  default     = "ubuntu22.04"
}

variable "flavor_name" {
  description = "Flavor name for both virtual machines"
  type        = string
  default     = "m1.small"
}

variable "app_node_name" {
  description = "Name of the App Node instance"
  type        = string
  default     = "app-node"
}

variable "vpn_node_name" {
  description = "Name of the VPN Gateway instance"
  type        = string
  default     = "vpn-gateway"
}

variable "private_net_name" {
  description = "Name of the private network for VPN/NAT"
  type        = string
  default     = "vpn_private_net"
}

variable "private_subnet_name" {
  description = "Name of the private subnet"
  type        = string
  default     = "vpn_private_subnet"
}

variable "private_subnet_cidr" {
  description = "CIDR block for the private network"
  type        = string
  default     = "10.0.0.0/24"
}

variable "app_net_name" {
  description = "Name of the isolated private network for App Node"
  type        = string
  default     = "app_private_net"
}

variable "app_subnet_name" {
  description = "Name of the isolated private subnet"
  type        = string
  default     = "app_private_subnet"
}

variable "app_subnet_cidr" {
  description = "CIDR block for the isolated private network"
  type        = string
  default     = "10.0.1.0/24"
}

variable "vpn_app_ip" {
  description = "Fixed IP address for the VPN Gateway port in the App network"
  type        = string
  default     = "10.0.1.254"
}

variable "router_name" {
  description = "Name of the OpenStack Router"
  type        = string
  default     = "vpn_router"
}
