# Terraform Provider Mirror + GitLab CI

## Назначение

Этот runbook описывает текущее состояние Terraform CI и внутреннего network mirror для Terraform provider `bpg/proxmox`.

Канонические внутренние сервисы:

```text
GitLab:   https://gitlab.int.romashlashes.by
Registry: https://registry.int.romashlashes.by
Mirror:   https://mirror.int.romashlashes.by
```

Временный namespace `romashlashes.test` выведен из эксплуатации.

## Архитектура

```text
Mac / VS Code
      │
      │ git push
      ▼
GitLab
gitlab.int.romashlashes.by
      │
      ▼
GitLab Runner
ci-01 / Docker executor
      │
      │ pulls CI image
      ▼
Container Registry
registry.int.romashlashes.by
      │
      ▼
terraform-ci:1.0.0
      │
      │ TF_CLI_CONFIG_FILE
      ▼
ci/terraform/terraform.tfrc
      │
      ▼
Terraform network mirror
mirror.int.romashlashes.by
      │
      ▼
registry.terraform.io/bpg/proxmox
provider version 0.114.0
```

## Компоненты

### GitLab

```text
Hostname: gitlab-01
IP:       192.168.0.187
URL:      https://gitlab.int.romashlashes.by
```

### Container Registry

```text
URL: https://registry.int.romashlashes.by
```

Terraform CI image:

```text
registry.int.romashlashes.by/romashlashes/romashlashes.by/terraform-ci:1.0.0
```

### GitLab Runner

```text
Hostname: ci-01
IP:       192.168.0.186
Executor: docker
```

Runner coordinator URL:

```text
https://gitlab.int.romashlashes.by
```

Проверка:

```bash
sudo gitlab-runner verify
```

### Terraform mirror

```text
Hostname: mirror-01
IP:       192.168.0.188
URL:      https://mirror.int.romashlashes.by
```

Health endpoint:

```text
https://mirror.int.romashlashes.by/healthz
```

Проверка:

```bash
curl -fsS https://mirror.int.romashlashes.by/healthz
```

Ожидается:

```text
ok
```

## Terraform provider

Используемый provider:

```text
registry.terraform.io/bpg/proxmox
```

Текущая версия:

```text
0.114.0
```

Terraform provider mirror хранит provider package и metadata, необходимые Terraform для установки provider без прямой загрузки с Terraform Registry.

## Terraform CLI configuration

Файл:

```text
ci/terraform/terraform.tfrc
```

Текущая конфигурация:

```hcl
provider_installation {
  network_mirror {
    url     = "https://mirror.int.romashlashes.by/providers/"
    include = ["registry.terraform.io/bpg/proxmox"]
  }

  direct {
    exclude = ["registry.terraform.io/bpg/proxmox"]
  }
}
```

Trailing slash в URL network mirror должен сохраняться:

```text
https://mirror.int.romashlashes.by/providers/
```

## GitLab CI

Terraform job использует CLI configuration из Git repository.

Переменная:

```text
TF_CLI_CONFIG_FILE=$CI_PROJECT_DIR/ci/terraform/terraform.tfrc
```

Таким образом URL mirror не требуется жёстко зашивать в Docker image.

Логика:

```text
terraform-check
      │
      ▼
Terraform binary
      │
      ▼
TF_CLI_CONFIG_FILE
      │
      ▼
ci/terraform/terraform.tfrc
      │
      ▼
mirror.int.romashlashes.by
```

## Почему CLI configuration хранится в Git

Environment-specific mirror URL хранится в репозитории, а не внутри immutable CI image.

Преимущества:

- смена mirror URL не требует пересборки CI image;
- configuration проходит code review;
- изменения видны в Git history;
- локальная и CI-конфигурация проще синхронизируются;
- меньше скрытых настроек внутри Docker image.

## CI image

Исходники образа:

```text
ci/terraform/
```

Основные файлы:

```text
ci/terraform/Dockerfile
ci/terraform/README.md
ci/terraform/terraform.tfrc
ci/terraform/romashlashes-rootCA.crt
```

CI image используется для запуска Terraform checks в GitLab Runner.

Проверить image reference:

```bash
grep -n 'terraform-ci' .gitlab-ci.yml
```

Ожидаемый registry hostname:

```text
registry.int.romashlashes.by
```

## Internal CA

Внутренние HTTPS-сервисы используют internal CA.

Для Terraform CI требуется доверие к:

```text
mirror.int.romashlashes.by
registry.int.romashlashes.by
gitlab.int.romashlashes.by
```

CA certificate для CI image:

```text
ci/terraform/romashlashes-rootCA.crt
```

Private CA key не должен храниться в Git.

## Проверка mirror metadata

Provider index:

```bash
curl -fsS \
  https://mirror.int.romashlashes.by/providers/registry.terraform.io/bpg/proxmox/index.json
```

Metadata версии:

```bash
curl -fsS \
  https://mirror.int.romashlashes.by/providers/registry.terraform.io/bpg/proxmox/0.114.0.json
```

Оба запроса должны выполняться без TLS ошибок.

## Локальная проверка Terraform

На Mac:

```bash
cd ~/romashlashes.by/terraform/proxmox
```

Проверка форматирования:

```bash
terraform fmt -check
```

Проверка конфигурации:

```bash
terraform validate
```

Для полной проверки установки provider через mirror можно удалить только локальный provider cache:

```bash
rm -rf .terraform
```

Не удалять:

```text
terraform.tfstate
terraform.tfstate.backup
```

Инициализация:

```bash
terraform init -backend=false
```

После этого:

```bash
terraform validate
```

## GitLab terraform-check

Для полного контрольного pipeline можно вручную запустить pipeline для ветки:

```text
main
```

В GitLab должны выполняться:

```text
django-check
terraform-check
ansible-check
```

После успешных checks вручную запускается:

```text
deploy-dev
```

Если обычный push не затрагивает Terraform-related files, `terraform-check` может не появляться из-за `rules: changes`.

Для полного контрольного запуска используется ручной pipeline через GitLab UI.

## Mirror Ansible role

Terraform mirror управляется Ansible role:

```text
ansible/roles/terraform_mirror
```

Playbook:

```text
ansible/playbooks/terraform-mirror.yml
```

Canonical Nginx server name:

```text
mirror.int.romashlashes.by
```

TLS certificate:

```text
mirror.int.romashlashes.by
```

Применение:

```bash
cd ~/romashlashes.by/ansible

ansible-playbook \
  -i inventory/hosts.yml \
  playbooks/terraform-mirror.yml \
  --ask-vault-pass
```

## Проверка TLS mirror

```bash
echo | openssl s_client \
  -connect mirror.int.romashlashes.by:443 \
  -servername mirror.int.romashlashes.by \
  2>/dev/null |
openssl x509 -noout -dates -ext subjectAltName
```

Ожидаемый SAN:

```text
DNS:mirror.int.romashlashes.by
```

## Проверка Nginx mirror

Health:

```bash
curl -fsS https://mirror.int.romashlashes.by/healthz
```

Ожидается:

```text
ok
```

Provider index:

```bash
curl -fsS \
  https://mirror.int.romashlashes.by/providers/registry.terraform.io/bpg/proxmox/index.json
```

## Обновление provider version

При обновлении `bpg/proxmox` необходимо синхронно проверить:

1. Terraform required provider version;
2. содержимое mirror;
3. provider metadata;
4. package checksum;
5. Terraform lock file;
6. CI pipeline.

После добавления новой версии mirror должен отдавать:

```text
/providers/registry.terraform.io/bpg/proxmox/index.json
```

и metadata соответствующей версии:

```text
/providers/registry.terraform.io/bpg/proxmox/<VERSION>.json
```

После обновления:

```bash
terraform init -upgrade
terraform validate
```

Изменения `.terraform.lock.hcl` должны быть просмотрены перед commit.

## Проверка Container Registry

Registry endpoint:

```bash
curl -I https://registry.int.romashlashes.by/v2/
```

Без авторизации нормальный ответ:

```text
HTTP 401
```

Authentication realm должен ссылаться на:

```text
https://gitlab.int.romashlashes.by/jwt/auth
```

Это подтверждает корректную связку:

```text
Registry
   ↓
GitLab authentication
```

## Проверка GitLab Runner

На `ci-01`:

```bash
sudo gitlab-runner verify
```

Проверить coordinator URL без вывода token:

```bash
sudo grep -nE \
'^[[:space:]]*(url|tls-ca-file)[[:space:]]*=' \
/etc/gitlab-runner/config.toml
```

Ожидается:

```text
url = "https://gitlab.int.romashlashes.by"
```

Runner CA:

```text
/etc/gitlab-runner/certs/romashlashes-rootCA.crt
```

Docker Registry trust:

```text
/etc/docker/certs.d/registry.int.romashlashes.by/ca.crt
```

## DNS

Mirror DNS:

```bash
dig @192.168.0.10 mirror.int.romashlashes.by A +short
dig @192.168.0.11 mirror.int.romashlashes.by A +short
```

Ожидается:

```text
mirror-01.int.romashlashes.by.
192.168.0.188
```

GitLab:

```text
gitlab.int.romashlashes.by -> 192.168.0.187
```

Registry:

```text
registry.int.romashlashes.by -> 192.168.0.187
```

## Миграция с временного namespace

Ранее Terraform CI использовал временные имена вида:

```text
gitlab.romashlashes.test
registry.romashlashes.test
mirror.romashlashes.test
```

После внедрения canonical DNS namespace все активные зависимости переведены на:

```text
gitlab.int.romashlashes.by
registry.int.romashlashes.by
mirror.int.romashlashes.by
```

Временная DNS zone выведена из эксплуатации.

`extra_hosts` для GitLab Runner больше не используется.

Terraform mirror URL теперь берётся из:

```text
ci/terraform/terraform.tfrc
```

## Troubleshooting

### Mirror health не отвечает

Проверить DNS:

```bash
dig @192.168.0.10 mirror.int.romashlashes.by A +short
```

Проверить HTTPS:

```bash
curl -v https://mirror.int.romashlashes.by/healthz
```

Проверить Nginx на `mirror-01`.

### Terraform сообщает x509 error

Проверить сертификат:

```bash
echo | openssl s_client \
  -connect mirror.int.romashlashes.by:443 \
  -servername mirror.int.romashlashes.by \
  2>/dev/null |
openssl x509 -noout -issuer -subject -ext subjectAltName
```

Проверить наличие internal CA в окружении, где запускается Terraform.

### Terraform идёт напрямую в Registry

Проверить:

```bash
echo "$TF_CLI_CONFIG_FILE"
```

В CI ожидается:

```text
$CI_PROJECT_DIR/ci/terraform/terraform.tfrc
```

Проверить содержимое:

```bash
cat ci/terraform/terraform.tfrc
```

### Provider version отсутствует

Проверить index:

```bash
curl -fsS \
  https://mirror.int.romashlashes.by/providers/registry.terraform.io/bpg/proxmox/index.json
```

Проверить version metadata:

```bash
curl -fsS \
  https://mirror.int.romashlashes.by/providers/registry.terraform.io/bpg/proxmox/0.114.0.json
```

### Runner не может скачать CI image

Проверить Registry:

```bash
curl -I https://registry.int.romashlashes.by/v2/
```

Проверить Runner:

```bash
sudo gitlab-runner verify
```

Проверить Docker CA:

```bash
sudo ls -l \
  /etc/docker/certs.d/registry.int.romashlashes.by/ca.crt
```

## Финальная проверка

Mirror:

```bash
curl -fsS https://mirror.int.romashlashes.by/healthz
```

Registry:

```bash
curl -I https://registry.int.romashlashes.by/v2/
```

GitLab:

```bash
curl -I https://gitlab.int.romashlashes.by/
```

Terraform:

```bash
cd ~/romashlashes.by/terraform/proxmox
terraform init -backend=false
terraform validate
```

GitLab full verification pipeline:

```text
django-check    -> passed
terraform-check -> passed
ansible-check   -> passed
deploy-dev      -> passed (manual)
```

После успешных проверок Terraform CI считается полностью переведённым на canonical namespace `int.romashlashes.by`.
