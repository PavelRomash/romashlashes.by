# GitLab CI/CD: DEV deployment

## Цель

Автоматизировать проверку Django-приложения и деплой DEV-окружения через self-hosted GitLab и GitLab Runner.

## Текущая схема

```text
Mac
  ↓ git push
Self-hosted GitLab
  ↓
GitLab Pipeline
  ├── django-check
  │     ├── Python 3.14
  │     ├── PostgreSQL 17 service
  │     ├── manage.py check
  │     ├── migrate
  │     ├── makemigrations --check
  │     └── tests
  │
  └── deploy-dev (manual)
        ↓
      Ansible
        ↓ SSH
      dev-01
        ↓
      Docker Compose
        ├── nginx
        ├── web / Django / Gunicorn
        └── PostgreSQL
```

DEV URL:

```text
https://dev.romashlashes.test
```

## Компоненты

### gitlab-01

Self-hosted GitLab server.

Назначение:

- хранение Git-репозитория;
- CI/CD pipelines;
- управление Runner;
- хранение CI/CD variables.

GitLab hostname:

```text
gitlab.romashlashes.test
```

### ci-01

Отдельная VM с GitLab Runner.

```text
Name: ci-01
Executor: docker
Tags:
  - docker
  - dev
```

Проверка:

```bash
sudo systemctl status gitlab-runner
sudo gitlab-runner verify
```

Runner config:

```text
/etc/gitlab-runner/config.toml
```

В Docker executor используется:

```toml
extra_hosts = ["gitlab.romashlashes.test:192.168.0.187"]
```

### dev-01

```text
IP: 192.168.0.185
```

На VM работают nginx, Django/Gunicorn и PostgreSQL.

```bash
cd /opt/romashlashes
sudo docker compose ps
```

## GitLab CI/CD variables

### ANSIBLE_SSH_PRIVATE_KEY

Type: `File`

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

Type: `File`

Пароль Ansible Vault для:

```text
ansible/inventory/group_vars/dev/vault.yml
```

## Django CI

Используются:

```text
python:3.14-slim
postgres:17
```

Проверки:

```bash
python manage.py check
python manage.py migrate --noinput
python manage.py makemigrations --check --dry-run
python manage.py test
```

## DEV deployment

Deployment job:

```text
deploy-dev
```

Сейчас запускается вручную после успешного `django-check`.

Ansible запускается так:

```bash
ansible-playbook   -i inventory/hosts.yml   playbooks/deploy-dev.yml   --vault-password-file "$ANSIBLE_VAULT_PASSWORD"
```

Ansible:

1. создаёт deployment artifact через `git archive`;
2. передаёт приложение на `dev-01`;
3. создаёт `.env`;
4. создаёт nginx config;
5. выполняет Docker Compose build/up;
6. проверяет HTTP → HTTPS redirect;
7. проверяет главную страницу;
8. проверяет static CSS.

## TLS

DEV TLS certificate уже хранится на `dev-01`:

```text
/opt/romashlashes/nginx/certs/
```

```text
dev.romashlashes.test.pem
dev.romashlashes.test-key.pem
```

TLS private key не передаётся через каждый pipeline.

## Post-deploy health checks

Главная:

```bash
curl   --fail   --silent   --show-error   --insecure   --resolve dev.romashlashes.test:443:192.168.0.185   https://dev.romashlashes.test/   --output /dev/null
```

CSS:

```bash
curl   --fail   --silent   --show-error   --insecure   --resolve dev.romashlashes.test:443:192.168.0.185   https://dev.romashlashes.test/static/css/styles.css   --output /dev/null
```

## Ручная проверка DEV

```bash
curl -I https://dev.romashlashes.test/
curl -I https://dev.romashlashes.test/static/css/styles.css
```

Ожидается `HTTP/1.1 200 OK`.

## Проверка Django production settings

```bash
cd /opt/romashlashes
sudo docker compose exec web python manage.py check --deploy
```

Для DEV сейчас допустимы:

```text
mail.W001
security.W004
```

## Troubleshooting

Runner:

```bash
sudo systemctl status gitlab-runner
sudo gitlab-runner verify
sudo journalctl -u gitlab-runner -n 100 --no-pager
```

Runner Docker hosts:

```bash
sudo grep extra_hosts /etc/gitlab-runner/config.toml
```

Vault:

```bash
cd ~/romashlashes.by/ansible
ansible-vault view inventory/group_vars/dev/vault.yml
```

Приложение:

```bash
ssh pavel@192.168.0.185
cd /opt/romashlashes

sudo docker compose ps
sudo docker compose logs --tail=100 web
sudo docker compose logs --tail=100 nginx
sudo docker compose logs --tail=100 postgres
```

## Текущая deployment policy

```text
git push
→ django-check автоматически
→ deploy-dev вручную
→ health checks автоматически
```

Автоматический deploy в `main` включим после стабилизации pipeline и backup/rollback процесса.
