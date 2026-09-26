resource "proxmox_virtual_environment_vm" "environment" {
  for_each = var.environments

  name      = "${each.key}-01"
  node_name = "pve"

  clone {
    vm_id = 9100
  }

  cpu {
    cores = each.value.cores
  }

  memory {
    dedicated = each.value.memory
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    size         = each.value.disk
  }

  agent {
    enabled = true

    wait_for_ip {
      ipv4 = true
    }
  }

  network_device {
    bridge = "vmbr0"
  }

  initialization {
    datastore_id = "local-lvm"

    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }

    user_account {
      username = "pavel"

      keys = [
        "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCpyup46jmsX88vNRKNKZZYAIus9oVx/Z0eUG6HQZmlVr7j7FK7itm4sh9XRFWJHi5GJu1UkAyisXNIKHDDaCBhROqiyJrdcu3WNCZmkP+9b7Vd5kIfBpUUucmQVWg/zMyiNIO54Kqz/CHJp2mjoA6xdz4Rj+a0Y0EdxRu61SyezLuJG7fjDK5oJKMBlNQ6IF7iQf7ASBdZ6GhjWMCJAZpR9To5Yls+f7taQZV7EcjC+Wh/2lDTeoRcjwfAFuSRLUc9uMgoyT2n76W3LE5uL5nb5CKqiGnktyyxOrS+maysErPCGjB8BL72ughe+ER8j5dmfAeY0OQpN+r05FQV9xMNqZAr6LHxKD5jDEmPW3fcO6BIzzEW8/XFwIpsX93I6nYYU38Gi49xZs6O4jBgvzDnpr56hrW3LWngWPqzybgIt0WGGqmbRo4/MuVjz3wl3YF+8zrY4tyalOtfGTaZmesSxpEzQEb0k3KXpzdgeJrPEBgOUrrJjwu551IDJSNfWUE= pavel@MacBook-Air-Pavel.local"
      ]
    }
  }
}