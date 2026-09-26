# Настройка Ansible inventory

## Цель

Подключить Ansible к существующим Terraform-managed окружениям:

- `dev-01`
- `stage-01`
- `prod-01`

Ansible запускается с Mac и подключается к VM по SSH как пользователь `pavel`.

## Текущие VM

```text
dev-01   → 192.168.0.185
stage-01 → 192.168.0.184
prod-01  → 192.168.0.183
```

## Структура Ansible

```text
ansible/
├── ansible.cfg
├── inventory/
│   └── hosts.yml
├── playbooks/
└── roles/
```

## `ansible.cfg`

Файл задаёт базовую конфигурацию Ansible:

```ini
[defaults]
inventory = inventory/hosts.yml
remote_user = pavel
host_key_checking = False
interpreter_python = auto_silent
```

### `inventory`

Указывает путь к inventory-файлу:

```text
inventory/hosts.yml
```

### `remote_user`

Все VM используют пользователя:

```text
pavel
```

### `host_key_checking`

В лабораторной инфраструктуре SSH host key checking временно отключён, чтобы пересозданные Terraform VM не требовали ручного подтверждения fingerprint.

### `interpreter_python`

```text
auto_silent
```

позволяет Ansible автоматически определить Python внутри VM.

В Debian 13 был автоматически найден:

```text
/usr/bin/python3.13
```

## Inventory

Файл:

```text
ansible/inventory/hosts.yml
```

содержит:

```yaml
all:
  children:
    dev:
      hosts:
        dev-01:
          ansible_host: 192.168.0.185

    stage:
      hosts:
        stage-01:
          ansible_host: 192.168.0.184

    prod:
      hosts:
        prod-01:
          ansible_host: 192.168.0.183
```

Используются отдельные группы:

```text
dev
stage
prod
```

Это позволит позже запускать конфигурацию выборочно.

Например:

```bash
ansible dev -m ping
```

или:

```bash
ansible prod -m ping
```

## Проверка inventory

Из каталога:

```bash
cd ~/romashlashes.by/ansible
```

проверить структуру:

```bash
ansible-inventory --graph
```

Ожидается:

```text
@all:
  |--@dev:
  |  |--dev-01
  |--@stage:
  |  |--stage-01
  |--@prod:
  |  |--prod-01
```

## Проверка соединения

Команда:

```bash
ansible all -m ping
```

Результат:

```text
dev-01   → SUCCESS / pong
stage-01 → SUCCESS / pong
prod-01  → SUCCESS / pong
```

Это подтверждает:

- inventory читается;
- SSH работает;
- пользователь `pavel` доступен;
- SSH key authentication работает;
- Python внутри VM найден;
- Ansible может выполнять модули на всех окружениях.

## Текущая схема

```text
Mac / VS Code
      ↓
    Ansible
      ↓
 inventory
      ↓
     SSH
      ↓
 ┌────┼─────┐
DEV STAGE PROD
```