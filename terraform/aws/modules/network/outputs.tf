output "vpc_id" {
  value = data.aws_vpc.main.id
}

output "public_subnet_id" {
  value = data.aws_subnet.public.id
}

output "route_table_id" {
  value = data.aws_route_table.public.id
}

output "vpc_cidr_block" {
  value = data.aws_vpc.main.cidr_block
}
