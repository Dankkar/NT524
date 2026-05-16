data "aws_vpc" "main" {
  id = var.vpc_id
}

data "aws_subnet" "public" {
  id = var.subnet_id
}

data "aws_route_table" "public" {
  route_table_id = var.route_table_id
}
