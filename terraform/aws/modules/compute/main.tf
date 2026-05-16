data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}

resource "aws_key_pair" "vpn_key" {
  key_name   = "aws_vpn_key"
  public_key = file(var.public_key_path)
}

resource "aws_instance" "vpn_gateway" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"
  subnet_id     = var.subnet_id
  key_name      = aws_key_pair.vpn_key.key_name

  vpc_security_group_ids = [var.vpn_sg_id]

  # Disable source/dest check to allow routing traffic for WAF
  source_dest_check = false

  user_data = <<-EOF
              #!/bin/bash
              apt-get update
              apt-get install -y wireguard iptables iptables-persistent
              
              echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
              sysctl -p
              
              DEFAULT_IFACE=$(ip route show default | awk '{print $5; exit}')
              iptables -t nat -A POSTROUTING -o $DEFAULT_IFACE -j MASQUERADE
              netfilter-persistent save
              EOF

  tags = {
    Name = "aws-vpn-gateway"
  }
}

resource "aws_instance" "waf_node" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"
  subnet_id     = var.subnet_id
  key_name      = aws_key_pair.vpn_key.key_name

  vpc_security_group_ids = [var.waf_sg_id]

  # Định tuyến traffic tới mạng OpenStack 10.0.0.0/16 thông qua VPN Gateway trên AWS.
  # (Sẽ thiết lập route sau khi VPN up, hoặc cấu hình qua Ansible).
  # Cài Nginx, ModSecurity, Filebeat sẽ được chạy bằng Ansible sau như thỏa thuận.
  user_data = <<-EOF
              #!/bin/bash
              # Nginx configuration will be provisioned by Ansible later
              EOF

  tags = {
    Name = "aws-waf-node"
  }

  depends_on = [aws_instance.vpn_gateway]
}

resource "aws_eip" "waf_eip" {
  domain   = "vpc"
  instance = aws_instance.waf_node.id
}

resource "aws_eip" "vpn_eip" {
  domain   = "vpc"
  instance = aws_instance.vpn_gateway.id
}
