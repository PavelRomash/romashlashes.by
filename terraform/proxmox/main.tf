resource "proxmox_virtual_environment_vm" "tf_test01" {
  name      = "tf-test01"
  node_name = "pve"

  cpu {
    cores = 2
  }

  memory {
    dedicated = 2048
  }

  network_device {
    bridge = "vmbr0"
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    size         = 20
  }
}