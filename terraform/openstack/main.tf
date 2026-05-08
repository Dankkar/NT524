module "network" {
  source              = "./modules/network"
  external_network_id = var.external_network_id
}

module "security_group" {
  source = "./modules/security_group"
}

module "compute" {
  source         = "./modules/compute"
  network_id     = module.network.private_network_id
  subnet_id      = module.network.private_subnet_id
  app_network_id = module.network.app_network_id
  app_subnet_id  = module.network.app_subnet_id
  app_sg_id      = module.security_group.app_sg_id
  vpn_sg_id      = module.security_group.vpn_sg_id
  floating_ip    = module.network.vpn_floating_ip
}
