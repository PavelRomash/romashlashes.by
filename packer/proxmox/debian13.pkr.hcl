source "proxmox-clone" "debian13" {
  proxmox_url = "https://192.168.0.176:8006/api2/json"
  node        = "pve"

  insecure_skip_tls_verify = true

  clone_vm = "debian-13-cloudinit-template"

  vm_id   = 9100
  vm_name = "debian-13-packer-builder"

  template_name        = "debian-13-packer-template"
  template_description = "Debian 13 template built with Packer"

  cores   = 2
  memory  = 2048
  sockets = 1

  os = "l26"

  scsi_controller = "virtio-scsi-pci"

  network_adapters {
    model  = "virtio"
    bridge = "vmbr0"
  }

  qemu_agent = true

  ipconfig {
    ip      = "192.168.0.189/24"
    gateway = "192.168.0.1"
  }

  cloud_init              = true
  cloud_init_storage_pool = "local-lvm"

  ssh_host     = "192.168.0.189"
  ssh_username = "pavel"
  ssh_timeout  = "10m"
}

build {
  sources = [
    "source.proxmox-clone.debian13"
  ]

  provisioner "shell" {
    inline = [
      "echo 'Waiting for cloud-init to finish...'",
      "sudo cloud-init status --wait || true",

      "echo 'Waiting for APT locks...'",
      "while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || sudo fuser /var/lib/dpkg/lock >/dev/null 2>&1 || sudo fuser /var/lib/apt/lists/lock >/dev/null 2>&1 || sudo fuser /var/cache/apt/archives/lock >/dev/null 2>&1; do sleep 2; done",

      "sudo apt-get update",
      "sudo apt-get install -y qemu-guest-agent",

      "sudo cloud-init clean --logs",
      "sudo truncate -s 0 /etc/machine-id",
      "sudo rm -f /var/lib/dbus/machine-id",
      "sudo rm -f /etc/ssh/ssh_host_*"
    ]
  }
}
