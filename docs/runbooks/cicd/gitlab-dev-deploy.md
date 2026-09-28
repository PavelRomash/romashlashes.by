# GitLab CI/CD: DEV deployment

## Цель

Автоматизировать проверки проекта и деплой DEV-окружения через self-hosted GitLab, GitLab Runner, Ansible и Docker Compose.

Документ описывает текущее состояние инфраструктуры после перехода с временного namespace `romashlashes.test` на канонический внутренний namespace `int.romashlashes.by`.

## Текущая схема

```text
Mac / VS Code
  ↓ git push
GitLab
https://gitlab.int.romashlashes.by
  ↓
GitLab Pipeline
  ├── django-check
  ├── terraform-check
  ├── ansible-check
  │
  └── deploy-dev (manual)
        ↓
      Ansible
        ↓ SSH
      dev-01
      192.168.0.185
        ↓
      Docker Compose
        ├── nginx
        ├── web / Django / Gunicorn
        └── PostgreSQL
```

DEV URL:

```text
https://dev.int.romashlashes.by
```

Внутреннее DNS-разрешение выполняется через:

```text
dns-01  192.168.0.10
dns-02  192.168.0.11
```

## Компоненты

### gitlab-01

Self-hosted GitLab server.

```text
Hostname: gitlab-01
IP:       192.168.0.187
URL:      https://gitlab.int.romashlashes.by
```

Назначение:

- хранение Git-репозитория;
- запуск CI/CD pipelines;
- управление GitLab Runner;
- хранение CI/CD variables;
- аутентификация Container Registry.

Container Registry:

```text
https://registry.int.romashlashes.by
```

### ci-01

Отдельная VM с GitLab Runner.

```text
Hostname: ci-01
IP:       192.168.0.186
Executor: docker
```

Проверка Runner:

```bash
sudo systemctl status gitlab-runner
sudo gitlab-runner verify
```

Конфигурация:

```text
/etc/gitlab-runner/config.toml
```

Runner подключается к:

```text
https://gitlab.int.romashlashes.by
```

Временные `extra_hosts` больше не используются. Имена внутренних сервисов разрешаются через BIND DNS.

Runner использует внутренний CA:

```text
/etc/gitlab-runner/certs/romashlashes-rootCA.crt
```

Docker доверяет Container Registry через:

```text
/etc/docker/certs.d/registry.int.romashlashes.by/ca.crt
```

### dev-01

```text
Hostname: dev-01
IP:       192.168.0.185
URL:      https://dev.int.romashlashes.by
```

На VM работают:

- Nginx;
- Django/Gunicorn;
- PostgreSQL.

Проверка:

```bash
cd /opt/romashlashes
sudo docker compose ps
```

Ожидаемые контейнеры:

```text
romashlashes-nginx
romashlashes-web
romashlashes-postgres
```

## GitLab CI/CD checks

Pipeline содержит проверки:

```text
django-check
terraform-check
ansible-check
```

Для полного контрольного запуска pipeline можно запустить вручную для ветки `main` через GitLab UI.

После успешных check jobs `deploy-dev` запускается вручную.

### django-check

Используются:

```text
python:3.14-slim
postgres:17
```

Основные проверки:

```bash
python manage.py check
python manage.py migrate --noinput
python manage.py makemigrations --check --dry-run
python manage.py test
```

### terraform-check

Проверяет Terraform-конфигурацию проекта.

Terraform использует внутренний provider mirror:

```text
https://mirror.int.romashlashes.by/providers/
```

CLI configuration хранится в репозитории:

```text
ci/terraform/terraform.tfrc
```

В CI используется:

```text
TF_CLI_CONFIG_FILE=$CI_PROJECT_DIR/ci/terraform/terraform.tfrc
```

### ansible-check

Проверяет Ansible-код проекта, включая lint и синтаксис playbooks.

Локальная проверка:

```bash
cd ~/romashlashes.by/ansible
ansible-lint
```

## GitLab CI/CD variables

### ANSIBLE_SSH_PRIVATE_KEY

Type:

```text
File
```

Отдельный приватный SSH-ключ для CI/CD deployment.

Проверка с Mac:

```bash
ssh -i ~/.ssh/romashlashes-ci-rsa pavel@192.168.0.185 hostname
```

Ожидается:

```text
dev-01
```

### ANSIBLE_VAULT_PASSWORD

Type:

```text
File
```

Используется Ansible для расшифровки:

```text
ansible/inventory/group_vars/dev/vault.yml
```

## DEV deployment

Deployment job:

```text
deploy-dev
```

Job запускается вручную после успешных проверок.

Ansible playbook:

```text
ansible/playbooks/deploy-dev.yml
```

Запуск Ansible в CI:

```bash
ansible-playbook \
  -i inventory/hosts.yml \
  playbooks/deploy-dev.yml \
  --vault-password-file "$ANSIBLE_VAULT_PASSWORD"
```

Во время deployment Ansible:

1. создаёт/распаковывает deployment artifact;
2. передаёт приложение на `dev-01`;
3. создаёт `.env`;
4. рендерит Nginx configuration;
5. выполняет Docker Compose build/up;
6. пересоздаёт Nginx-контейнер при изменении Nginx configuration;
7. проверяет HTTP → HTTPS;
8. проверяет главную страницу;
9. проверяет static CSS.

## Nginx

Шаблон:

```text
ansible/roles/app_deploy/templates/nginx.conf.j2
```

Текущий DEV server name:

```text
dev.int.romashlashes.by
```

На `dev-01` сгенерированный файл:

```text
/opt/romashlashes/nginx/default.conf
```

Он монтируется в контейнер:

```text
/opt/romashlashes/nginx/default.conf
  ->
/etc/nginx/conf.d/default.conf
```

TLS certificate directory:

```text
/opt/romashlashes/nginx/certs
  ->
/etc/nginx/certs
```

Проверка активной конфигурации:

```bash
sudo docker exec romashlashes-nginx \
  nginx -T 2>&1 |
grep -E 'server_name|ssl_certificate'
```

Ожидается:

```text
server_name dev.int.romashlashes.by;
ssl_certificate /etc/nginx/certs/dev.int.romashlashes.by.pem;
ssl_certificate_key /etc/nginx/certs/dev.int.romashlashes.by-key.pem;
```

### Почему при изменении Nginx config нужен recreate

`default.conf` подключён в контейнер как file bind mount.

Ansible `template` атомарно заменяет файл на хосте. Уже запущенный Docker container может продолжать использовать старый inode, поэтому обычного `nginx -s reload` недостаточно.

В роли `app_deploy` изменение Nginx template вызывает handler, который пересоздаёт только сервис `nginx`.

Это гарантирует, что новый bind mount будет подключён к актуальному файлу.

## TLS

Текущий DEV certificate:

```text
/opt/romashlashes/nginx/certs/dev.int.romashlashes.by.pem
```

Private key:

```text
/opt/romashlashes/nginx/certs/dev.int.romashlashes.by-key.pem
```

Текущий сертификат содержит canonical SAN:

```text
DNS:dev.int.romashlashes.by
```

Проверка с Mac:

```bash
echo | openssl s_client \
  -connect dev.int.romashlashes.by:443 \
  -servername dev.int.romashlashes.by \
  2>/dev/null |
openssl x509 -noout -ext subjectAltName
```

Ожидается:

```text
DNS:dev.int.romashlashes.by
```

TLS private key не хранится в Git.

## Post-deploy health checks

Внутренний DNS уже настроен, поэтому `--resolve` больше не требуется.

TLS проверяется штатно, поэтому `--insecure` также не требуется.

Главная страница:

```bash
curl \
  --fail \
  --silent \
  --show-error \
  https://dev.int.romashlashes.by/ \
  --output /dev/null
```

Static CSS:

```bash
curl \
  --fail \
  --silent \
  --show-error \
  https://dev.int.romashlashes.by/static/css/styles.css \
  --output /dev/null
```

## Ручная проверка DEV

Главная страница:

```bash
curl -I https://dev.int.romashlashes.by/
```

Static CSS:

```bash
curl -I https://dev.int.romashlashes.by/static/css/styles.css
```

Ожидается:

```text
HTTP/1.1 200 OK
```

DNS:

```bash
dig @192.168.0.10 dev.int.romashlashes.by A +short
dig @192.168.0.11 dev.int.romashlashes.by A +short
```

Ожидаемый адрес:

```text
192.168.0.185
```

## Проверка Django production settings

На `dev-01`:

```bash
cd /opt/romashlashes
sudo docker compose exec web python manage.py check --deploy
```

Для DEV отдельные security warnings могут быть допустимы только если это осознанно отражено в конфигурации окружения.

## Проверка всего стека после изменений

Полный контрольный сценарий:

```text
1. Push в GitLab
2. django-check
3. terraform-check
4. ansible-check
5. deploy-dev вручную
6. Проверить HTTPS DEV
7. Проверить активный Nginx config
8. Проверить TLS SAN
```

Проверка сервисов:

```bash
curl -I https://gitlab.int.romashlashes.by/
curl -I https://registry.int.romashlashes.by/v2/
curl -fsS https://mirror.int.romashlashes.by/healthz
curl -I https://dev.int.romashlashes.by/
```

Нормальные ответы:

```text
GitLab   -> HTTP 302 на /users/sign_in
Registry -> HTTP 401 без авторизации
Mirror   -> ok
DEV      -> HTTP 200
```

## Troubleshooting

### GitLab Runner

```bash
sudo systemctl status gitlab-runner
sudo gitlab-runner verify
sudo journalctl -u gitlab-runner -n 100 --no-pager
```

### DEV containers

```bash
cd /opt/romashlashes
sudo docker compose ps
```

### Nginx syntax

```bash
sudo docker exec romashlashes-nginx nginx -t
```

### Активная Nginx configuration

```bash
sudo docker exec romashlashes-nginx \
  nginx -T 2>&1 |
grep -E 'server_name|ssl_certificate'
```

### DEV logs

```bash
cd /opt/romashlashes
sudo docker compose logs --tail=100 nginx
sudo docker compose logs --tail=100 web
sudo docker compose logs --tail=100 postgres
```

### DNS

```bash
dig @192.168.0.10 dev.int.romashlashes.by A +short
dig @192.168.0.11 dev.int.romashlashes.by A +short
```

### TLS

```bash
echo | openssl s_client \
  -connect dev.int.romashlashes.by:443 \
  -servername dev.int.romashlashes.by \
  2>/dev/null |
openssl x509 -noout -dates -ext subjectAltName
```

## Текущее состояние

Канонические внутренние имена:

```text
gitlab.int.romashlashes.by   -> 192.168.0.187
registry.int.romashlashes.by -> 192.168.0.187
mirror.int.romashlashes.by   -> 192.168.0.188
dev.int.romashlashes.by      -> 192.168.0.185
```

Временный namespace `romashlashes.test` выведен из эксплуатации и больше не используется runtime-конфигурацией проекта.
