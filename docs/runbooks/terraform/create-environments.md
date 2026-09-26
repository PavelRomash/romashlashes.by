# Создание DEV / STAGE / PROD через Terraform

## Цель

Создать три постоянных окружения проекта из одного подготовленного Proxmox template:

```text
dev
stage
prod
```

Все VM должны:

- клонироваться из Packer template `9100`;
- создаваться через Terraform;
- получать IPv4 через DHCP;
- использовать Cloud-Init;
- иметь пользователя `pavel`;
- принимать SSH public key;
- использовать QEMU Guest Agent;
- автоматически отдавать IPv4 обратно Terraform.

---

## Исходный template

Для рабочих VM используется:

```text
VMID: 9100
Name: debian-13-packer-template
```

Template создан через Packer и содержит:

```text
Debian 13
Cloud-Init
qemu-guest-agent
virtio-scsi-pci
agent enabled
очищенный machine-id
очищенные SSH host keys
```

---

## Структура Terraform

```text
terraform/proxmox/
├── main.tf
├── variables.tf
├── outputs.tf
├── provider.tf
└── versions.tf
```

Каждый файл отвечает за свою часть конфигурации.

---

# `versions.tf`

Определяет зависимости Terraform.

Для Proxmox используется provider:

```text
bpg/proxmox
```

После:

```bash
terraform init
```

Terraform загружает provider и фиксирует выбранную версию в:

```text
.terraform.lock.hcl
```

---

# `provider.tf`

Определяет подключение к Proxmox.

Используется endpoint:

```text
https://192.168.0.176:8006/
```

TLS verification отключено для локального self-signed сертификата.

API token не хранится в Terraform-файлах.

Он передаётся через environment variable:

```bash
export PROXMOX_VE_API_TOKEN='terraform@pve!provider=SECRET'
```

Secret нельзя хранить в Git.

---

# `variables.tf`

Определяет окружения и их ресурсы.

Используется map:

```hcl
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
  }
}
```

На текущем этапе все окружения имеют одинаковые ресурсы.

Позже их можно изменить независимо друг от друга, например:

```text
dev   → 2 CPU / 2 GB
stage → 2 CPU / 4 GB
prod  → 4 CPU / 8 GB
```

без изменения логики создания VM.

---

# `main.tf`

Главный файл инфраструктуры.

Используется один resource:

```hcl
resource "proxmox_virtual_environment_vm" "environment" {
  for_each = var.environments
```

`for_each` создаёт отдельную VM для каждого элемента:

```text
dev
stage
prod
```

Terraform state содержит их как:

```text
proxmox_virtual_environment_vm.environment["dev"]
proxmox_virtual_environment_vm.environment["stage"]
proxmox_virtual_environment_vm.environment["prod"]
```

---

## Имена VM

```hcl
name = "${each.key}-01"
```

Поэтому создаются:

```text
dev-01
stage-01
prod-01
```

---

## Clone source

```hcl
clone {
  vm_id = 9100
}
```

Все VM создаются клонированием Packer template `9100`.

Debian заново не устанавливается.

---

## CPU

```hcl
cpu {
  cores = each.value.cores
}
```

Количество CPU берётся из `variables.tf`.

---

## Memory

```hcl
memory {
  dedicated = each.value.memory
}
```

RAM также задаётся отдельно для каждого environment.

---

## Disk

```hcl
disk {
  datastore_id = "local-lvm"
  interface    = "scsi0"
  size         = each.value.disk
}
```

VM используют:

```text
storage: local-lvm
interface: scsi0
```

Размер диска берётся из `variables.tf`.

---

## QEMU Guest Agent

```hcl
agent {
  enabled = true

  wait_for_ip {
    ipv4 = true
  }
}
```

Terraform ждёт, пока QEMU Guest Agent внутри VM сообщит IPv4.

Это позволяет избежать ручного поиска IP через Proxmox Console или ARP/neighbor table.

---

## Network

```hcl
network_device {
  bridge = "vmbr0"
}
```

VM подключаются к основной LAN через Proxmox bridge:

```text
vmbr0
```

---

## Cloud-Init

```hcl
initialization {
  datastore_id = "local-lvm"

  ip_config {
    ipv4 {
      address = "dhcp"
    }
  }
```

При первом запуске VM получает IP через DHCP.

---

## User

Cloud-Init создаёт:

```text
pavel
```

и добавляет SSH public key:

```hcl
user_account {
  username = "pavel"

  keys = [
    "ssh-rsa ..."
  ]
}
```

Пароль в Terraform не используется.

Основной административный доступ выполняется через SSH key.

---

# `outputs.tf`

Собирает IPv4 всех окружений:

```hcl
output "vm_ipv4_addresses" {
  value = {
    for environment, vm in proxmox_virtual_environment_vm.environment :
    environment => vm.ipv4_addresses
  }
}
```

После `terraform apply` Terraform показывает адреса всех VM.

---

# Проверка конфигурации

Форматирование:

```bash
terraform fmt
```

Проверка:

```bash
terraform validate
```

Ожидается:

```text
Success! The configuration is valid.
```

---

# План

```bash
terraform plan
```

При переходе со старой тестовой VM `tf_test01` Terraform показал:

```text
Plan: 3 to add, 0 to change, 1 to destroy.
```

Это означало:

```text
удалить:
tf_test01

создать:
dev-01
stage-01
prod-01
```

---

# Создание окружений

```bash
terraform apply
```

Результат:

```text
Apply complete! Resources: 3 added, 0 changed, 1 destroyed.
```

---

# Созданные VM

Terraform создал:

```text
dev-01   → 192.168.0.185
stage-01 → 192.168.0.184
prod-01  → 192.168.0.183
```

IP получены автоматически через QEMU Guest Agent.

---

# Проверка SSH

Проверено подключение ко всем VM:

```bash
ssh pavel@192.168.0.185
ssh pavel@192.168.0.184
ssh pavel@192.168.0.183
```

SSH работает на всех трёх окружениях.

---

# Текущая архитектура

```text
Proxmox
│
├── 9000
│   └── raw Debian 13 GenericCloud template
│
├── 9001
│   └── вручную подготовленный Debian template
│
├── 9100
│   └── Packer-built Debian template
│
├── dev-01
│   └── 192.168.0.185
│
├── stage-01
│   └── 192.168.0.184
│
└── prod-01
    └── 192.168.0.183
```

---

# Ответственность инструментов

```text
Packer
→ создаёт базовый VM image/template

Terraform
→ создаёт VM и инфраструктуру

Cloud-Init
→ выполняет первоначальную конфигурацию VM

QEMU Guest Agent
→ передаёт Proxmox информацию из гостевой ОС

SSH
→ административный доступ
```

Следующий слой проекта:

```text
Ansible
→ конфигурация созданных серверов
```

Итоговая модель:

```text
Packer
→ какой образ

Terraform
→ какие VM существуют

Ansible
→ как эти VM настроены
```