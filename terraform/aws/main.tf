module "network" {
  source = "./modules/network"
}

module "security_group" {
  source = "./modules/security_group"
  vpc_id = module.network.vpc_id
}

module "compute" {
  source          = "./modules/compute"
  subnet_id       = module.network.public_subnet_id
  waf_sg_id       = module.security_group.waf_sg_id
  vpn_sg_id       = module.security_group.vpn_sg_id
  public_key_path = var.public_key_path
}
