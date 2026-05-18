module "network" {
  source         = "./modules/network"
  vpc_id         = var.vpc_id
  subnet_id      = var.subnet_id
  route_table_id = var.route_table_id
}

module "security_group" {
  source                    = "./modules/security_group"
  vpc_id                    = module.network.vpc_id
  vpc_cidr_block            = module.network.vpc_cidr_block
  openstack_vpn_public_cidr = var.openstack_vpn_public_cidr
}

module "compute" {
  source                   = "./modules/compute"
  subnet_id                = module.network.public_subnet_id
  waf_sg_id                = module.security_group.waf_sg_id
  vpn_sg_id                = module.security_group.vpn_sg_id
  public_key_path          = var.public_key_path
  keypair_name             = var.keypair_name
  instance_type            = var.instance_type
  vpn_node_name            = var.vpn_node_name
  waf_node_name            = var.waf_node_name
  waf_iam_instance_profile = aws_iam_instance_profile.waf_ec2.name
}

resource "aws_route" "openstack_app_via_vpn" {
  route_table_id         = module.network.route_table_id
  destination_cidr_block = var.openstack_app_cidr
  network_interface_id   = module.compute.vpn_network_interface_id
}
