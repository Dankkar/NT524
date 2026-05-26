module "network" {
  source              = "./modules/network"
  external_network_id = var.external_network_id
  floating_ip_pool    = var.floating_ip_pool
  private_net_name    = var.private_net_name
  private_subnet_name = var.private_subnet_name
  private_subnet_cidr = var.private_subnet_cidr
  waf_net_name        = var.waf_net_name
  waf_subnet_name     = var.waf_subnet_name
  waf_subnet_cidr     = var.waf_subnet_cidr
  app_net_name        = var.app_net_name
  app_subnet_name     = var.app_subnet_name
  app_subnet_cidr     = var.app_subnet_cidr
  router_name         = var.router_name
}

module "security_group" {
  source           = "./modules/security_group"
  app_subnet_cidr  = var.app_subnet_cidr
  waf_subnet_cidr  = var.waf_subnet_cidr
  db_allowed_cidrs = var.db_allowed_cidrs
}

module "compute" {
  source         = "./modules/compute"
  network_id     = module.network.private_network_id
  subnet_id      = module.network.private_subnet_id
  waf_network_id = module.network.waf_network_id
  waf_subnet_id  = module.network.waf_subnet_id
  app_network_id = module.network.app_network_id
  app_subnet_id  = module.network.app_subnet_id
  vpn_sg_id      = module.security_group.vpn_sg_id
  waf_sg_id      = module.security_group.waf_sg_id
  app_sg_name    = module.security_group.app_sg_name
  vpn_sg_name    = module.security_group.vpn_sg_name
  waf_sg_name    = module.security_group.waf_sg_name
  db_sg_name     = module.security_group.db_sg_name
  floating_ip    = module.network.vpn_floating_ip

  keypair_name    = var.keypair_name
  public_key_path = var.public_key_path
  image_name      = var.image_name
  flavor_name     = var.flavor_name
  app_node_name   = var.app_node_name
  waf_node_name   = var.waf_node_name
  db_node_name    = var.db_node_name
  vpn_node_name   = var.vpn_node_name
  vpn_app_ip      = var.vpn_app_ip
  vpn_waf_ip      = var.vpn_waf_ip
  waf_transit_ip  = var.waf_transit_ip
  app_subnet_cidr = var.app_subnet_cidr
}
