variable "dns_servers" {
  description = "Internal DNS virtual machines"

  type = map(object({
    cores        = number
    memory       = number
    disk         = number
    ipv4_address = string
  }))

  default = {
    dns-01 = {
      cores        = 1
      memory       = 512
      disk         = 20
      ipv4_address = "192.168.0.10/24"
    }

    dns-02 = {
      cores        = 1
      memory       = 512
      disk         = 20
      ipv4_address = "192.168.0.11/24"
    }
  }
}

variable "lan_gateway" {
  description = "Default gateway for statically addressed infrastructure VMs"
  type        = string
  default     = "192.168.0.1"
}

variable "internal_dns_domain" {
  description = "Canonical internal DNS search domain"
  type        = string
  default     = "int.romashlashes.by"
}

variable "dns_bootstrap_resolvers" {
  description = "Resolvers used by DNS VMs before BIND is configured"
  type        = list(string)
  default     = ["192.168.0.1"]
}
