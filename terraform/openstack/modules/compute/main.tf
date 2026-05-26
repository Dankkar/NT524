terraform {
  required_providers {
    openstack = {
      source = "terraform-provider-openstack/openstack"
    }
  }
}
resource "openstack_compute_keypair_v2" "openstack_key" {
  name       = var.keypair_name
  public_key = file(var.public_key_path)
}

resource "openstack_compute_instance_v2" "app_node" {
  name            = var.app_node_name
  image_name      = var.image_name
  flavor_name     = var.flavor_name
  key_pair        = openstack_compute_keypair_v2.openstack_key.name
  security_groups = [var.app_sg_name]

  network {
    uuid = var.app_network_id
  }

  # WAF is the default gateway into the app/database network.
  depends_on = [openstack_compute_instance_v2.vpn_gateway, openstack_compute_instance_v2.waf_node]

  user_data = <<-EOF
                #!/bin/bash
                sleep 30
                ip route del 8.8.8.8 || true
                ip route del 8.8.4.4 || true
                
                ip route del default || true
                ip route add default via ${var.vpn_app_ip}
                
                echo "nameserver 8.8.8.8" > /etc/resolv.conf
                EOF
}

resource "openstack_networking_port_v2" "waf_transit_port" {
  name               = "${var.waf_node_name}_transit_port"
  network_id         = var.waf_network_id
  security_group_ids = [var.waf_sg_id]

  fixed_ip {
    subnet_id  = var.waf_subnet_id
    ip_address = var.waf_transit_ip
  }

  allowed_address_pairs {
    ip_address = "0.0.0.0/0"
  }
}

resource "openstack_networking_port_v2" "waf_app_port" {
  name               = "${var.waf_node_name}_app_port"
  network_id         = var.app_network_id
  security_group_ids = [var.waf_sg_id]

  fixed_ip {
    subnet_id  = var.app_subnet_id
    ip_address = var.vpn_app_ip
  }

  allowed_address_pairs {
    ip_address = "0.0.0.0/0"
  }
}

resource "openstack_compute_instance_v2" "waf_node" {
  name            = var.waf_node_name
  image_name      = var.image_name
  flavor_name     = var.flavor_name
  key_pair        = openstack_compute_keypair_v2.openstack_key.name
  security_groups = [var.waf_sg_name]

  network {
    port = openstack_networking_port_v2.waf_transit_port.id
  }

  network {
    port = openstack_networking_port_v2.waf_app_port.id
  }

  depends_on = [openstack_compute_instance_v2.vpn_gateway]

  user_data = <<-EOF
                #!/bin/bash
                sleep 30
                ip route del 8.8.8.8 || true
                ip route del 8.8.4.4 || true

                ip route del default || true
                ip route add default via ${var.vpn_waf_ip}

                echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
                sysctl -p

                echo "nameserver 8.8.8.8" > /etc/resolv.conf
                EOF
}

resource "openstack_compute_instance_v2" "db_node" {
  name            = var.db_node_name
  image_name      = var.image_name
  flavor_name     = var.flavor_name
  key_pair        = openstack_compute_keypair_v2.openstack_key.name
  security_groups = [var.db_sg_name]

  network {
    uuid = var.app_network_id
  }

  depends_on = [openstack_compute_instance_v2.vpn_gateway, openstack_compute_instance_v2.waf_node]

  user_data = <<-EOF
                #!/bin/bash
                sleep 30
                ip route del 8.8.8.8 || true
                ip route del 8.8.4.4 || true

                ip route del default || true
                ip route add default via ${var.vpn_app_ip}

                echo "nameserver 8.8.8.8" > /etc/resolv.conf
                EOF
}

resource "openstack_networking_port_v2" "vpn_waf_port" {
  name               = "${var.vpn_node_name}_waf_port"
  network_id         = var.waf_network_id
  security_group_ids = [var.vpn_sg_id]

  fixed_ip {
    subnet_id  = var.waf_subnet_id
    ip_address = var.vpn_waf_ip
  }

  allowed_address_pairs {
    ip_address = "0.0.0.0/0"
  }
}

resource "openstack_compute_instance_v2" "vpn_gateway" {
  name            = var.vpn_node_name
  image_name      = var.image_name
  flavor_name     = var.flavor_name
  key_pair        = openstack_compute_keypair_v2.openstack_key.name
  security_groups = [var.vpn_sg_name]

  # Mạng ra Internet
  network {
    uuid = var.network_id
  }

  # Transit network to WAF. VPN Gateway no longer connects directly to app/db net.
  network {
    port = openstack_networking_port_v2.vpn_waf_port.id
  }

  user_data = <<-EOF
              #!/bin/bash
              echo "nameserver 8.8.8.8" > /etc/resolv.conf
              ip route del 8.8.8.8 || true
              ip route del 8.8.4.4 || true

              apt-get update
              echo iptables-persistent iptables-persistent/autosave_v4 boolean true | debconf-set-selections
              echo iptables-persistent iptables-persistent/autosave_v6 boolean true | debconf-set-selections
              DEBIAN_FRONTEND=noninteractive apt-get install -y wireguard iptables iptables-persistent
              
              echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
              sysctl -p
              ip route add ${var.app_subnet_cidr} via ${var.waf_transit_ip} || true
              DEFAULT_IFACE=$(ip route show default | awk '{print $5; exit}')
              iptables -t nat -A POSTROUTING -o $DEFAULT_IFACE -j MASQUERADE
              netfilter-persistent save
              EOF
}

resource "openstack_compute_floatingip_associate_v2" "fip_assoc" {
  floating_ip = var.floating_ip
  instance_id = openstack_compute_instance_v2.vpn_gateway.id
}
