# Создание Debian 13 template через Packer

## Цель

Автоматизировать ручную подготовку Debian 13 template.

Packer должен:

```text
9000 Debian GenericCloud template
        ↓
clone
        ↓
temporary builder VM
        ↓
Cloud-Init
        ↓
SSH
        ↓
установка qemu-guest-agent
        ↓
очистка образа
        ↓
template 9100
```

Итоговый template:

```text
9100 — debian-13-packer-template
```

должен быть полностью готов для использования Terraform.

---

## 1. Установить Packer

На Mac:

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/packer
```

Проверить:

```bash
packer version
which packer
```

В нашей конфигурации использовался:

```text
Packer v1.14.3
```

---

## 2. Создать структуру проекта

```bash
cd ~/romashlashes.by

mkdir -p packer/proxmox/scripts

cd packer/proxmox
```

Структура:

```text
packer/
└── proxmox/
    ├── plugins.pkr.hcl
    ├── debian13.pkr.hcl
    └── scripts/
```

---

## 3. Подключить Proxmox plugin

Создать:

```text
plugins.pkr.hcl
```

Содержимое:

```hcl
packer {
  required_plugins {
    proxmox = {
      version = "~> 1.2"
      source  = "github.com/hashicorp/proxmox"
    }
  }
}
```

Установить plugin:

```bash
packer init .
```

Проверить:

```bash
packer plugins installed
```

В нашей сборке использовался:

```text
github.com/hashicorp/proxmox v1.2.4
```

---

## 4. Создать API token для Packer

Выполняется на Proxmox:

```bash
pveum user token add terraform@pve packer --privsep=0
```

Полученный secret нельзя сохранять в Git.

На Mac:

```bash
export PROXMOX_URL='https://192.168.0.176:8006/api2/json'
export PROXMOX_USERNAME='terraform@pve!packer'
export PROXMOX_TOKEN='SECRET'
```

Проверить наличие, не выводя secret:

```bash
test -n "$PROXMOX_TOKEN" && echo "Packer token: OK"
```

---

## 5. Packer configuration

Создать:

```text
debian13.pkr.hcl
```

Рабочая конфигурация:

```hcl
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

  cloud_init              = true
  cloud_init_storage_pool = "local-lvm"

  ipconfig {
    ip      = "192.168.0.189/24"
    gateway = "192.168.0.1"
  }

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
```

---

## 6. Почему используется статический builder IP

Исходный template `9000` не содержит установленного QEMU Guest Agent.

Поэтому на первом этапе Packer не может использовать Guest Agent для определения IPv4.

Используется временный адрес:

```text
192.168.0.189
```

и:

```hcl
ssh_host = "192.168.0.189"
```

Адрес должен быть свободен и не конфликтовать с DHCP.

Этот IP используется только во время Packer build.

Рабочие VM, создаваемые Terraform из готового template, используют DHCP.

---

## 7. Почему нужен virtio-scsi-pci

Исходный template `9000` использует:

```text
scsihw: virtio-scsi-pci
```

Поэтому в Packer явно указывается:

```hcl
scsi_controller = "virtio-scsi-pci"
```

Без этого builder VM у нас загрузилась в:

```text
(initramfs)
```

и Debian не смог продолжить загрузку.

---

## 8. Почему Packer ждёт Cloud-Init

Первоначальная версия provisioner сразу выполняла:

```bash
apt-get update
```

но Cloud-Init ещё выполнял собственный package operation.

Результат:

```text
Could not get lock /var/lib/apt/lists/lock
```

Поэтому сначала выполняется:

```bash
sudo cloud-init status --wait
```

А затем дополнительно ожидается освобождение APT/DPKG locks.

Только после этого выполняется:

```bash
sudo apt-get update
sudo apt-get install -y qemu-guest-agent
```

---

## 9. Почему qemu_agent = true

Финальный template должен иметь одновременно:

```text
Proxmox:
agent: 1
```

и внутри Debian:

```text
qemu-guest-agent installed
```

Поэтому используется:

```hcl
qemu_agent = true
```

При этом на этапе bootstrap Packer всё равно подключается напрямую:

```hcl
ssh_host = "192.168.0.189"
```

После установки `qemu-guest-agent` итоговый template уже полностью готов.

---

## 10. Проверить конфигурацию

```bash
packer fmt .
```

```bash
packer validate .
```

Ожидается:

```text
The configuration is valid.
```

---

## 11. Запустить сборку

```bash
packer build .
```

Успешная сборка выглядит примерно так:

```text
Creating ephemeral key pair for SSH communicator
Creating VM
Starting VM
Waiting for SSH
Connected to SSH
Waiting for cloud-init to finish
Waiting for APT locks
Installing qemu-guest-agent
Stopping VM
Converting VM to template
Adding a cloud-init cdrom
```

Финал:

```text
A template was created: 9100
```

---

## 12. Проверить готовый template

На Proxmox:

```bash
qm config 9100 | grep -E 'agent|template|scsihw'
```

Рабочий результат:

```text
agent: 1
scsihw: virtio-scsi-pci
template: 1
```

---

## 13. Проверка через Terraform

В Terraform:

```hcl
clone {
  vm_id = 9100
}
```

Agent:

```hcl
agent {
  enabled = true

  wait_for_ip {
    ipv4 = true
  }
}
```

После:

```bash
terraform apply
```

Terraform должен автоматически получить IP через QEMU Guest Agent.

В нашей проверке VM получила:

```text
192.168.0.181
```

Terraform output:

```text
tf_test01_ipv4 = [
  [
    "127.0.0.1",
  ],
  [
    "192.168.0.181",
  ],
]
```

Это подтверждает работу всей цепочки:

```text
Packer
↓
Proxmox template
↓
Terraform
↓
Cloud-Init
↓
QEMU Guest Agent
↓
автоматическое определение IPv4
```

---

# Найденные проблемы

## Builder падает в initramfs

Причина:

```text
неподходящий SCSI controller
```

Исправление:

```hcl
scsi_controller = "virtio-scsi-pci"
```

---

## Packer бесконечно ждёт SSH

Проверить:

```bash
qm cloudinit dump <VMID> network
qm cloudinit dump <VMID> user
```

У builder должны быть:

```text
IP
user
temporary Packer SSH key
```

---

## apt lock

Ошибка:

```text
Could not get lock /var/lib/apt/lists/lock
```

Причина — Cloud-Init ещё использует APT.

Решение:

```bash
cloud-init status --wait
```

и ожидание освобождения APT/DPKG locks.

---

## Итоговый template имеет agent: 0

Причина:

```hcl
qemu_agent = false
```

Решение:

```hcl
qemu_agent = true
```

Финальный результат:

```text
agent: 1
template: 1
```

---

# Результат

Ручной процесс подготовки template полностью автоматизирован.

Теперь обычная пересборка выполняется одной командой:

```bash
packer build .
```

и создаёт:

```text
9100
└── debian-13-packer-template
    ├── Debian 13
    ├── Cloud-Init
    ├── QEMU Guest Agent installed
    ├── agent enabled
    ├── virtio-scsi-pci
    ├── очищенный machine-id
    ├── очищенные SSH host keys
    └── готовность к Terraform
```