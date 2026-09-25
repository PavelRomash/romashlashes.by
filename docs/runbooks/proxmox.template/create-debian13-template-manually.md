# Создание Debian 13 Cloud-Init template вручную в Proxmox

## Цель

Создать базовый Debian 13 template для Proxmox, пригодный для автоматического клонирования через Terraform.

Готовый template должен содержать:

- Debian 13 GenericCloud;
- Cloud-Init;
- QEMU Guest Agent;
- VirtIO SCSI;
- DHCP;
- очищенный `machine-id`;
- очищенные SSH host keys;
- очищенное состояние Cloud-Init.

В нашей лаборатории:

```text
9000 — исходный Debian GenericCloud template
9001 — подготовленный вручную Debian 13 template
```

---

## 1. Скачать Debian 13 GenericCloud

Выполняется на **Proxmox host**:

```bash
mkdir -p /var/lib/vz/template/qcow2
cd /var/lib/vz/template/qcow2
```

Скачать образ:

```bash
wget https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2
```

---

## 2. Создать исходную VM

```bash
qm create 9000 \
  --name debian-13-cloudinit-template \
  --memory 2048 \
  --cores 2 \
  --net0 virtio,bridge=vmbr0
```

Импортировать диск:

```bash
qm disk import \
  9000 \
  debian-13-genericcloud-amd64.qcow2 \
  local-lvm
```

Подключить диск:

```bash
qm set 9000 \
  --scsihw virtio-scsi-pci \
  --scsi0 local-lvm:vm-9000-disk-0
```

Добавить Cloud-Init drive:

```bash
qm set 9000 --ide2 local-lvm:cloudinit
```

Настроить загрузку:

```bash
qm set 9000 --boot order=scsi0
```

Добавить serial console:

```bash
qm set 9000 --serial0 socket --vga serial0
```

Превратить VM в template:

```bash
qm template 9000
```

Проверить:

```bash
qm config 9000
```

Особенно:

```text
scsihw: virtio-scsi-pci
template: 1
boot: order=scsi0
```

---

## 3. Создать builder VM

Исходный GenericCloud template не содержит установленного QEMU Guest Agent.

Клонируем его:

```bash
qm clone 9000 9001 \
  --name debian-13-base-builder \
  --full
```

Включаем QEMU Agent на уровне Proxmox:

```bash
qm set 9001 --agent enabled=1
```

Важно:

```text
agent enabled=1
```

не устанавливает `qemu-guest-agent` внутрь Debian.

Это только добавляет соответствующее виртуальное устройство.

---

## 4. Настроить Cloud-Init

Настроить DHCP:

```bash
qm set 9001 --ipconfig0 ip=dhcp
```

Создать пользователя:

```bash
qm set 9001 --ciuser pavel
```

На Mac посмотреть public SSH key:

```bash
cat ~/.ssh/id_rsa.pub
```

На Proxmox создать временный файл:

```bash
nano /root/pavel_id_rsa.pub
```

Вставить public key.

Передать его Cloud-Init:

```bash
qm set 9001 --sshkeys /root/pavel_id_rsa.pub
```

---

## 5. Проверить Cloud-Init

Сеть:

```bash
qm cloudinit dump 9001 network
```

Должен присутствовать DHCP:

```yaml
subnets:
  - type: dhcp4
```

Пользователь:

```bash
qm cloudinit dump 9001 user
```

Должны присутствовать:

```yaml
user: pavel
ssh_authorized_keys:
```

---

## 6. Временно назначить известный IP

На этапе первоначальной подготовки Guest Agent ещё отсутствует, поэтому Proxmox не обязательно сможет автоматически показать IPv4 VM.

В нашей лаборатории временно использовался:

```text
192.168.0.189
```

Перед использованием адрес должен быть свободен и не конфликтовать с DHCP.

Настроить:

```bash
qm set 9001 \
  --ipconfig0 ip=192.168.0.189/24,gw=192.168.0.1
```

Полностью перезапустить VM:

```bash
qm stop 9001
qm start 9001
```

---

## 7. Подключиться по SSH

С Mac:

```bash
ssh pavel@192.168.0.189
```

---

## 8. Установить QEMU Guest Agent

Внутри builder VM:

```bash
sudo apt update
sudo apt install -y qemu-guest-agent
```

Запустить:

```bash
sudo systemctl start qemu-guest-agent
```

Проверить:

```bash
sudo systemctl status qemu-guest-agent
```

Ожидается:

```text
Active: active (running)
```

В Debian 13 сервис является static unit, поэтому предупреждение при:

```bash
systemctl enable qemu-guest-agent
```

не является ошибкой.

---

## 9. Подготовить VM к превращению в template

Очистить состояние Cloud-Init:

```bash
sudo cloud-init clean --logs
```

Очистить `machine-id`:

```bash
sudo truncate -s 0 /etc/machine-id
sudo rm -f /var/lib/dbus/machine-id
```

Удалить SSH host keys:

```bash
sudo rm -f /etc/ssh/ssh_host_*
```

Это необходимо, чтобы новые VM получали уникальные идентификаторы и SSH host keys.

---

## 10. Выключить builder

```bash
sudo shutdown -h now
```

На Proxmox проверить:

```bash
qm status 9001
```

Ожидается:

```text
status: stopped
```

---

## 11. Создать template

```bash
qm template 9001
```

Вернуть DHCP:

```bash
qm set 9001 --ipconfig0 ip=dhcp
```

Проверить:

```bash
qm config 9001 | grep -E 'agent|ipconfig0|template|scsihw'
```

Ожидается примерно:

```text
agent: enabled=1
ipconfig0: ip=dhcp
scsihw: virtio-scsi-pci
template: 1
```

---

# Troubleshooting

## Proxmox не показывает IPv4

Это не обязательно означает отсутствие сети.

До установки QEMU Guest Agent Proxmox не может надёжно получить сетевые интерфейсы гостевой системы.

Проверять внутри VM:

```bash
ip addr
```

Команда:

```bash
ip neigh show dev vmbr0
```

не является надёжным способом обнаружения IP всех VM.

---

## QEMU Guest Agent не запускается

Проверить:

```bash
ls -l /dev/virtio-ports/
```

Должно существовать:

```text
org.qemu.guest_agent.0
```

Если устройства нет:

```bash
qm set <VMID> --agent enabled=1
qm stop <VMID>
qm start <VMID>
```

После этого внутри VM:

```bash
sudo systemctl start qemu-guest-agent
```

---

## Cloud-Init показывает degraded

Проверить:

```bash
cloud-init status --long
```

У Debian 13 может появляться предупреждение о deprecated поле:

```text
'user' of type string is deprecated
```

Если:

```text
errors: []
```
