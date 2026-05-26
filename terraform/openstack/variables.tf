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
  default     = "openstack_key"
}

variable "public_key_path" {
  description = "Path to the SSH public key file"
  type        = string
  default     = "~/.ssh/openstack_key.pub"
}

variable "image_name" {
  description = "Image name for both virtual machines"
  type        = string
  default     = "Ubuntu-24.04"
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

variable "waf_node_name" {
  description = "Name of the WAF Node instance"
  type        = string
  default     = "waf-node"
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

variable "waf_net_name" {
  description = "Name of the transit network between VPN Gateway and WAF Node"
  type        = string
  default     = "waf_private_net"
}

variable "waf_subnet_name" {
  description = "Name of the transit subnet between VPN Gateway and WAF Node"
  type        = string
  default     = "waf_private_subnet"
}

variable "waf_subnet_cidr" {
  description = "CIDR block for the transit network between VPN Gateway and WAF Node"
  type        = string
  default     = "10.0.2.0/24"
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
  description = "Fixed IP address for the WAF Node port in the App network"
  type        = string
  default     = "10.0.1.254"
}

variable "vpn_waf_ip" {
  description = "Fixed IP address for the VPN Gateway port in the WAF transit network"
  type        = string
  default     = "10.0.2.254"
}

variable "waf_transit_ip" {
  description = "Fixed IP address for the WAF Node port in the WAF transit network"
  type        = string
  default     = "10.0.2.10"
}

variable "db_node_name" {
  description = "Name of the centralized Database Node instance"
  type        = string
  default     = "db-node"
}

variable "db_allowed_cidrs" {
  description = "CIDR ranges allowed to reach PostgreSQL on the centralized DB node"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "172.31.0.0/16", "10.200.0.0/24"]
}

variable "router_name" {
  description = "Name of the OpenStack Router"
  type        = string
  default     = "vpn_router"
}
