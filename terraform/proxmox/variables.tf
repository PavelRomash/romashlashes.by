variable "environments" {
  description = "Virtual machines for project environments"

  type = map(object({
    cores  = number
    memory = number
    disk   = number
  }))

  default = {
    dev = {
      cores  = 2
      memory = 2048
      disk   = 20
    }

    stage = {
      cores  = 2
      memory = 2048
      disk   = 20
    }

    prod = {
      cores  = 2
      memory = 2048
      disk   = 20
    }

    ci = {
      cores  = 2
      memory = 2048
      disk   = 20
    }

  }
}