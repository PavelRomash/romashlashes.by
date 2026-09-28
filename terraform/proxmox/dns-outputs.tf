output "dns_vm_names" {
  description = "DNS VM names managed by Terraform"
  value       = { for key, vm in proxmox_virtual_environment_vm.dns : key => vm.name }
}

output "dns_ipv4_addresses" {
  description = "Configured static IPv4 addresses for DNS VMs"
  value       = { for key, cfg in var.dns_servers : key => cfg.ipv4_address }
}
