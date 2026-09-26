output "vm_ipv4_addresses" {
  value = {
    for environment, vm in proxmox_virtual_environment_vm.environment :
    environment => vm.ipv4_addresses
  }
}