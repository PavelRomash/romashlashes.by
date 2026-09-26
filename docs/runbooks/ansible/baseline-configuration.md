# Baseline configuration with Ansible

## Цель

Привести DEV, STAGE и PROD к одинаковому базовому состоянию через Ansible.

Playbook:

```text
ansible/playbooks/baseline.yml
```

применяется ко всем VM:

```text
dev-01
stage-01
prod-01
```

## Playbook

```yaml
---
- name: Configure baseline settings
  hosts: all
  become: true

  tasks:
    - name: Update apt cache
      ansible.builtin.apt:
        update_cache: true
        cache_valid_time: 3600

    - name: Install baseline packages
      ansible.builtin.apt:
        name:
          - curl
          - wget
          - git
          - ca-certificates
          - jq
          - vim
          - htop
          - unzip
          - chrony
        state: present

    - name: Ensure chrony is enabled and running
      ansible.builtin.service:
        name: chrony
        state: started
        enabled: true
      when: not ansible_check_mode
```

## `hosts: all`

Playbook применяется ко всем узлам из inventory:

```text
DEV
STAGE
PROD
```

## `become: true`

Задачи выполняются через `sudo`, когда нужны root-права.

Например:

```text
apt install
systemctl
```

## Обновление APT cache

```yaml
ansible.builtin.apt:
  update_cache: true
  cache_valid_time: 3600
```

Это эквивалентно:

```bash
sudo apt update
```

но Ansible не обновляет cache повторно, если он обновлялся менее часа назад.

## Базовые пакеты

Устанавливаются:

```text
curl
wget
git
ca-certificates
jq
vim
htop
unzip
chrony
```

Ansible гарантирует состояние:

```text
state: present
```

То есть пакет должен быть установлен.

Если пакет уже существует, повторно ничего не меняется.

## Chrony

`chrony` используется для синхронизации времени.

Ansible гарантирует:

```text
service started
+
enabled at boot
```

## Check mode

Перед реальным применением использовался:

```bash
ansible-playbook playbooks/baseline.yml --check
```

Первоначально задача запуска `chrony` завершалась ошибкой:

```text
Could not find the requested service chrony
```

Причина:

```text
--check
↓
Ansible показывает, что chrony был бы установлен
↓
но реально пакет не устанавливает
↓
следующая task пытается найти ещё не существующий service
```

Поэтому для service task добавлено:

```yaml
when: not ansible_check_mode
```

В dry-run сервис пропускается.

## Реальное применение

Команда:

```bash
ansible-playbook playbooks/baseline.yml
```

При первом запуске:

```text
dev-01   changed=1 failed=0
stage-01 changed=1 failed=0
prod-01  changed=1 failed=0
```

Это означает, что необходимые изменения были применены.

## Проверка идемпотентности

Playbook был запущен повторно:

```bash
ansible-playbook playbooks/baseline.yml
```

Результат:

```text
dev-01   changed=0 failed=0
stage-01 changed=0 failed=0
prod-01  changed=0 failed=0
```

Это подтверждает идемпотентность.

## Что такое идемпотентность

Ansible описывает не последовательность ручных команд, а желаемое состояние системы.

Первый запуск:

```text
текущее состояние
        ↓
Ansible
        ↓
желаемое состояние
```

Повторный запуск:

```text
желаемое состояние уже достигнуто
        ↓
Ansible
        ↓
changed=0
```

Это позволяет безопасно запускать playbook повторно.

## Текущая модель управления

```text
Packer
→ создаёт базовый Debian template

Terraform
→ создаёт DEV / STAGE / PROD VM

Ansible
→ приводит операционные системы к нужному состоянию
```

То есть:

```text
Image as Code
      ↓
Infrastructure as Code
      ↓
Configuration as Code
```

## Ansible role structure

Baseline configuration was moved from a monolithic playbook into a reusable role.

Current structure:

~~~text
ansible/
├── playbooks/
│   └── baseline.yml
└── roles/
    └── baseline/
        ├── defaults/
        │   └── main.yml
        ├── handlers/
        │   └── main.yml
        ├── tasks/
        │   └── main.yml
        └── templates/
            └── chrony.conf.j2
~~~

The playbook now defines where the configuration is applied:

~~~yaml
---
- name: Configure baseline settings
  hosts: all
  become: true

  roles:
    - baseline
~~~

The role contains the actual configuration logic.

## Role variables

Baseline packages and system settings are stored in:

~~~text
roles/baseline/defaults/main.yml
~~~

Example:

~~~yaml
baseline_packages:
  - curl
  - wget
  - git
  - ca-certificates
  - jq
  - vim
  - htop
  - unzip
  - chrony

baseline_timezone: Europe/Amsterdam
baseline_locale: C.UTF-8
~~~

This separates configuration data from task logic.

## Timezone and locale

The baseline role configures:

~~~text
Timezone: Europe/Amsterdam
Locale:   C.UTF-8
~~~

Timezone was verified with:

~~~bash
timedatectl
~~~

Locale was verified with:

~~~bash
locale
~~~

An additional macOS SSH issue was discovered.

The Mac originally used:

~~~text
LC_CTYPE=UTF-8
~~~

and macOS SSH propagated locale variables using:

~~~text
/etc/ssh/ssh_config.d/100-macos.conf
SendEnv LANG LC_*
~~~

The Mac locale was corrected to:

~~~text
LC_CTYPE=C.UTF-8
~~~

After reconnecting over SSH, Debian received a valid locale without errors.

## Chrony template and handler

Chrony configuration is managed using an Ansible template:

~~~text
roles/baseline/templates/chrony.conf.j2
~~~

The template task notifies a handler:

~~~yaml
notify: Restart chrony
~~~

The handler is located in:

~~~text
roles/baseline/handlers/main.yml
~~~

It restarts Chrony only when the configuration file actually changes.

This prevents unnecessary service restarts.

## Idempotency verification

After all role changes, the playbook was executed again.

Result:

~~~text
dev-01   changed=0 failed=0
stage-01 changed=0 failed=0
prod-01  changed=0 failed=0
~~~

This confirms that the baseline role is idempotent.