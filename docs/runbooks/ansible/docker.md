# Docker installation with Ansible

## Цель

Установить Docker Engine на все окружения:

- `dev-01`
- `stage-01`
- `prod-01`

Установка выполняется через отдельную Ansible role:

~~~text
ansible/roles/docker/
~~~

## Структура

~~~text
ansible/
├── playbooks/
│   └── docker.yml
└── roles/
    └── docker/
        ├── defaults/
        │   └── main.yml
        └── tasks/
            └── main.yml
~~~

## Переменные роли

Файл:

~~~text
roles/docker/defaults/main.yml
~~~

содержит список Docker-пакетов:

~~~yaml
docker_packages:
  - docker-ce
  - docker-ce-cli
  - containerd.io
  - docker-buildx-plugin
  - docker-compose-plugin
~~~

Также задаются пользователи, которым разрешено запускать Docker без sudo:

~~~yaml
docker_users:
  - pavel
~~~

## Docker APT repository

Docker устанавливается не через convenience script, а через официальный APT repository.

Role выполняет следующие шаги:

~~~text
Install prerequisites
        ↓
Create /etc/apt/keyrings
        ↓
Download Docker GPG key
        ↓
Add Docker APT repository
        ↓
apt update
        ↓
Install Docker Engine
        ↓
Enable and start Docker
        ↓
Add user to docker group
~~~

## GPG key

Docker GPG key сохраняется в:

~~~text
/etc/apt/keyrings/docker.asc
~~~

Он используется APT для проверки пакетов из Docker repository.

## Устанавливаемые компоненты

~~~text
docker-ce
docker-ce-cli
containerd.io
docker-buildx-plugin
docker-compose-plugin
~~~

### docker-ce

Docker Engine.

### docker-ce-cli

CLI-клиент `docker`.

### containerd.io

Container runtime, который используется Docker.

### docker-buildx-plugin

Расширенная система сборки Docker images.

### docker-compose-plugin

Добавляет команду:

~~~bash
docker compose
~~~

## Playbook

Файл:

~~~text
playbooks/docker.yml
~~~

~~~yaml
---
- name: Install and configure Docker
  hosts: all
  become: true

  roles:
    - docker
~~~

## Check mode limitation

При запуске:

~~~bash
ansible-playbook playbooks/docker.yml --check
~~~

Ansible сообщил:

~~~text
No package matching 'docker-ce' is available
~~~

Причина в том, что в check mode Docker repository только прогнозируется как изменённый, но реально не создаётся.

Поэтому следующая APT task ещё не видит пакет:

~~~text
docker-ce
~~~

При обычном запуске repository создаётся физически и установка проходит успешно.

## Проверка установки

Docker version:

~~~bash
ansible all -a "docker --version"
~~~

Docker Compose:

~~~bash
ansible all -a "docker compose version"
~~~

Docker service:

~~~bash
ansible all -b -a "systemctl is-active docker"
~~~

Ожидаемый результат:

~~~text
active
~~~

на всех трёх VM.

## Идемпотентность

После повторного запуска:

~~~bash
ansible-playbook playbooks/docker.yml
~~~

role не должна вносить лишние изменения.

Это подтверждает, что Docker configuration управляется декларативно через Ansible.