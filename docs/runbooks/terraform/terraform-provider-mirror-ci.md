# Terraform Provider Mirror and GitLab CI

## 1. Зачем это было нужно

GitLab Runner на `ci-01` не мог выполнить `terraform init`, потому что доступ к публичному Terraform Registry (`registry.terraform.io`) блокировался по географическому признаку (Беларусь).

Ошибка возникала не в Terraform-коде и не в Proxmox. Проблема была именно в загрузке Terraform provider `bpg/proxmox`.

Вместо VPN или внешнего proxy была построена внутренняя схема:

```text
GitLab
  |
  v
GitLab Runner (ci-01)
  |
  | pull CI image
  v
GitLab Container Registry
  |
  v
terraform-ci:1.0.0
  |
  | terraform init
  v
Terraform Provider Mirror (mirror-01)
  |
  v
bpg/proxmox 0.114.0
```

Теперь CI не зависит от прямого доступа к `registry.terraform.io` для provider `bpg/proxmox`.

---

## 2. Что в итоге построено

### GitLab

Хост:

```text
gitlab-01
192.168.0.187
```

Имена:

```text
gitlab.romashlashes.test
registry.romashlashes.test
```

GitLab работает по HTTPS.

Container Registry работает по HTTPS:

```text
https://registry.romashlashes.test
```

Проверка Registry:

```bash
curl -i https://registry.romashlashes.test/v2/
```

Ожидаемый ответ без авторизации:

```text
HTTP/1.1 401 Unauthorized
Docker-Distribution-Api-Version: registry/2.0
WWW-Authenticate: Bearer ...
```

`401 Unauthorized` в данном случае означает, что Registry работает и требует аутентификацию.

---

## 3. GitLab Runner

Runner расположен на:

```text
ci-01
192.168.0.186
```

Используется Docker executor.

Runner подключается к GitLab по HTTPS:

```toml
url = "https://gitlab.romashlashes.test"
tls-ca-file = "/etc/gitlab-runner/certs/gitlab.romashlashes.test.crt"
```

Runner должен разрешать внутренние DNS-имена внутри job-контейнеров.

До появления внутреннего DNS используется:

```toml
extra_hosts = [
  "gitlab.romashlashes.test:192.168.0.187",
  "mirror.romashlashes.test:192.168.0.188"
]
```

Проверка Runner:

```bash
sudo gitlab-runner verify
```

---

## 4. Terraform Provider Mirror

Mirror расположен на:

```text
mirror-01
192.168.0.188
```

DNS-имя:

```text
mirror.romashlashes.test
```

Mirror обслуживается nginx по HTTPS.

Основной URL:

```text
https://mirror.romashlashes.test/providers/
```

Health check:

```bash
curl -i https://mirror.romashlashes.test/healthz
```

Ожидается:

```text
HTTP/1.1 200 OK
```

### Provider

В mirror хранится:

```text
registry.terraform.io/bpg/proxmox
```

Закреплённая версия:

```text
0.114.0
```

Поддерживаемые платформы:

```text
linux_amd64
darwin_arm64
```

Структура:

```text
/providers/
└── registry.terraform.io/
    └── bpg/
        └── proxmox/
            ├── index.json
            ├── 0.114.0.json
            ├── terraform-provider-proxmox_0.114.0_linux_amd64.zip
            └── terraform-provider-proxmox_0.114.0_darwin_arm64.zip
```

Mirror разворачивается через Ansible:

```text
ansible/roles/terraform_mirror/
ansible/playbooks/terraform-mirror.yml
```

---

## 5. Почему Terraform всё ещё пишет `registry.terraform.io/bpg/proxmox`

Это имя provider, а не обязательно адрес, с которого Terraform физически скачивает ZIP.

Canonical provider address:

```text
registry.terraform.io/bpg/proxmox
```

Terraform CLI configuration говорит Terraform:

> Для этого provider не обращайся напрямую в публичный Registry. Используй наш внутренний mirror.

Конфигурация:

```hcl
provider_installation {
  network_mirror {
    url     = "https://mirror.romashlashes.test/providers/"
    include = ["registry.terraform.io/bpg/proxmox"]
  }

  direct {
    exclude = ["registry.terraform.io/bpg/proxmox"]
  }
}
```

То есть логически provider остаётся:

```text
registry.terraform.io/bpg/proxmox
```

но физически скачивается с:

```text
mirror.romashlashes.test
```

---

## 6. Зачем появился Docker image `terraform-ci`

Раньше GitLab job использовал:

```yaml
image: hashicorp/terraform:latest
```

Внутри стандартного image не было:

- нашего внутреннего CA;
- конфигурации Terraform mirror;
- зафиксированной рабочей версии Terraform для проекта.

Поэтому был создан свой CI image:

```text
terraform-ci:1.0.0
```

Полное имя:

```text
registry.romashlashes.test/romashlashes/romashlashes.by/terraform-ci:1.0.0
```

Image содержит:

```text
Terraform 1.16.4
internal Root CA
/etc/terraformrc
```

Provider в Docker image НЕ хранится.

Provider по-прежнему скачивается с `mirror-01`.

---

## 7. Dockerfile CI image

Исходники расположены:

```text
ci/terraform/
```

Файлы:

```text
ci/terraform/
├── Dockerfile
├── terraform.tfrc
├── README.md
└── romashlashes-rootCA.crt
```

Важно:

```text
romashlashes-rootCA.crt
```

является публичным сертификатом CA.

Это НЕ приватный ключ.

В Git запрещено помещать:

```text
rootCA-key.pem
*.key
private keys
Deploy Tokens
Runner tokens
Vault passwords
```

---

## 8. TLS и сертификаты простыми словами

В инфраструктуре есть внутренний Certificate Authority.

Он нужен, чтобы наши внутренние HTTPS-сервисы могли использовать нормальный TLS:

```text
gitlab.romashlashes.test
registry.romashlashes.test
mirror.romashlashes.test
```

### Root CA certificate

Пример:

```text
romashlashes-rootCA.crt
```

Это публичная часть.

Её можно устанавливать на серверы и помещать внутрь CI image.

Она говорит:

> Я доверяю сертификатам, подписанным этим CA.

### Root CA private key

Например:

```text
rootCA-key.pem
```

Это секрет.

Он используется для выпуска новых сертификатов.

Его нельзя:

- коммитить;
- помещать в Docker image;
- передавать в GitLab job;
- хранить на Runner без необходимости.

---

## 9. Почему CA устанавливался в нескольких местах

Это не дублирование одной и той же задачи.

Есть несколько независимых клиентов HTTPS.

### GitLab Runner -> GitLab

Runner должен доверять:

```text
https://gitlab.romashlashes.test
```

Поэтому CA нужен GitLab Runner.

### Docker daemon -> GitLab Registry

Docker daemon должен доверять:

```text
https://registry.romashlashes.test
```

Поэтому CA установлен в:

```text
/etc/docker/certs.d/registry.romashlashes.test/ca.crt
```

### terraform-ci container -> mirror

Terraform внутри контейнера должен доверять:

```text
https://mirror.romashlashes.test
```

Поэтому публичный Root CA встроен в `terraform-ci`.

Это три разных процесса:

```text
gitlab-runner
dockerd
terraform inside container
```

У каждого своё TLS-окружение.

---

## 10. Deploy Token

Deploy Token использовался только для первоначальной ручной загрузки image в GitLab Container Registry.

Его scopes:

```text
read_registry
write_registry
```

Он использовался для:

```bash
docker login
docker push
```

После bootstrap:

```bash
docker logout registry.romashlashes.test
```

и shell-переменные были очищены:

```bash
unset REGISTRY_USER
unset REGISTRY_TOKEN
```

Обычный GitLab CI job не должен хранить этот Deploy Token в `.gitlab-ci.yml`.

Для доступа к Container Registry того же GitLab-проекта GitLab Runner использует job credentials.

---

## 11. Зачем Container Registry

Можно было оставить image только локально на `ci-01`, но это плохая архитектура.

Тогда Runner зависел бы от случайного локального состояния конкретного сервера.

Сейчас image хранится централизованно:

```text
GitLab Container Registry
```

Преимущества:

- versioning;
- воспроизводимость;
- можно удалить локальный image и скачать снова;
- Runner не зависит от ручной подготовки `/var/lib/docker`;
- позже можно использовать этот же image на других Runner.

Контрольная проверка уже выполнена:

```text
docker push -> OK
docker rmi -> OK
docker pull -> OK
terraform version -> Terraform v1.16.4
```

---

## 12. Почему image имеет версию `1.0.0`

Используется:

```text
terraform-ci:1.0.0
```

а не:

```text
terraform-ci:latest
```

Это позволяет точно знать, какое окружение использовал pipeline.

Позже изменения должны выпускаться как новая версия, например:

```text
terraform-ci:1.0.1
terraform-ci:1.1.0
terraform-ci:2.0.0
```

---

## 13. Почему image собирался с `--provenance=false`

При первой публикации Docker/BuildKit создал OCI manifest list с дополнительной provenance attestation.

GitLab Registry при финальной публикации вернул:

```text
blob unknown to registry
```

Для нашего single-platform CI image provenance и SBOM на данном этапе не требуются.

Image был пересобран:

```bash
sudo docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  --load \
  -t registry.romashlashes.test/romashlashes/romashlashes.by/terraform-ci:1.0.0 \
  .
```

После этого push прошёл успешно.

---

## 14. Текущий Terraform GitLab CI job

```yaml
terraform-check:
  stage: test
  image:
    name: registry.romashlashes.test/romashlashes/romashlashes.by/terraform-ci:1.0.0
    entrypoint: [""]

  tags:
    - docker
    - dev

  before_script:
    - cd terraform/proxmox
    - terraform version

  script:
    - terraform fmt -check -recursive
    - terraform init -backend=false
    - terraform validate

  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      changes:
        - terraform/**/*
        - ci/terraform/**/*
        - .gitlab-ci.yml
```

Этот job уже успешно прошёл.

---

## 15. Что происходит при каждом `terraform-check`

### Шаг 1

GitLab видит новый commit.

### Шаг 2

GitLab Runner на `ci-01` получает job.

### Шаг 3

Docker Runner скачивает:

```text
terraform-ci:1.0.0
```

из:

```text
registry.romashlashes.test
```

### Шаг 4

В контейнере выполняется:

```bash
cd terraform/proxmox
terraform version
```

### Шаг 5

Запускается:

```bash
terraform fmt -check -recursive
```

Проверяется формат Terraform-кода.

### Шаг 6

Запускается:

```bash
terraform init -backend=false
```

Terraform читает:

```text
/etc/terraformrc
```

и видит:

```text
bpg/proxmox -> internal mirror
```

### Шаг 7

Terraform скачивает provider с:

```text
https://mirror.romashlashes.test/providers/
```

### Шаг 8

Запускается:

```bash
terraform validate
```

Проверяется корректность Terraform configuration.

---

## 16. Что эта схема НЕ делает

`terraform-check` НЕ выполняет:

```bash
terraform apply
```

Он не создаёт и не удаляет VM.

Он только проверяет Terraform-код.

Также:

```bash
terraform init -backend=false
```

не подключает рабочий remote backend.

Это специально для CI validation job.

---

## 17. Разделение ответственности

### Proxmox

Запускает VM.

### Terraform

Описывает и создаёт VM/инфраструктуру.

### Ansible

Настраивает ОС и сервисы внутри VM.

### Docker

Запускает изолированные CI environments и приложения.

### GitLab

Хранит Git repository и управляет pipeline.

### GitLab Runner

Исполняет pipeline jobs.

### GitLab Container Registry

Хранит Docker images.

### mirror-01

Хранит утверждённые Terraform provider packages.

---

## 18. Где что находится

```text
Mac
├── Git repository
├── Terraform code
├── Ansible code
└── CI image source
        |
        | git push
        v
GitLab
        |
        | job
        v
ci-01
├── GitLab Runner
└── Docker
     |
     | pull
     v
GitLab Container Registry
     |
     v
terraform-ci
     |
     | terraform init
     v
mirror-01
     |
     v
bpg/proxmox provider
```

---

## 19. Проверки

### GitLab HTTPS

```bash
curl -I https://gitlab.romashlashes.test
```

### Registry

```bash
curl -i https://registry.romashlashes.test/v2/
```

Без логина ожидается `401 Unauthorized`.

### Mirror

```bash
curl -i https://mirror.romashlashes.test/healthz
```

Ожидается `200 OK`.

### Runner

На `ci-01`:

```bash
sudo gitlab-runner verify
```

### Docker Registry trust

На `ci-01`:

```bash
sudo docker pull registry.romashlashes.test/nonexistent/image:latest
```

Ошибка доступа допустима.

Ошибка:

```text
x509: certificate signed by unknown authority
```

недопустима.

### CI image

```bash
sudo docker run --rm \
  registry.romashlashes.test/romashlashes/romashlashes.by/terraform-ci:1.0.0 \
  terraform version
```

Ожидается:

```text
Terraform v1.16.4
on linux_amd64
```

---

## 20. Обновление Terraform provider

Не заменять ZIP вручную без фиксации версии и checksum.

Порядок:

1. выбрать новую версию provider;
2. получить официальные release artifacts;
3. проверить SHA256;
4. обновить Ansible role mirror;
5. применить role на `mirror-01`;
6. обновить `.terraform.lock.hcl`;
7. проверить Mac;
8. проверить CI;
9. commit.

---

## 21. Обновление `terraform-ci`

Если меняется:

- версия Terraform;
- internal CA;
- `terraform.tfrc`;
- системные пакеты image;

следует выпустить новую версию image.

Например:

```text
1.0.0 -> 1.0.1
```

Собрать:

```bash
docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  --sbom=false \
  --load \
  -t registry.romashlashes.test/romashlashes/romashlashes.by/terraform-ci:1.0.1 \
  .
```

Push:

```bash
docker push \
  registry.romashlashes.test/romashlashes/romashlashes.by/terraform-ci:1.0.1
```

Затем изменить `.gitlab-ci.yml`.

---

## 22. Security rules

Никогда не коммитить:

```text
Terraform API tokens
GitLab Runner tokens
Deploy Tokens
Vault passwords
SSH private keys
TLS private keys
rootCA-key.pem
```

Допустимо хранить:

```text
public Root CA certificate
public TLS certificates
checksums
provider metadata
Terraform lock file
```

Перед commit:

```bash
git status
git diff --cached
```

Полезно:

```bash
git status --ignored
git check-ignore <file>
```

---

## 23. Текущие временные ограничения

### `/etc/hosts`

Сейчас внутренние имена частично разрешаются через `/etc/hosts` и Runner `extra_hosts`.

Это приемлемо для текущей lab/production-like инфраструктуры, но следующим инфраструктурным улучшением должен стать внутренний DNS.

Тогда:

```text
gitlab.romashlashes.test
registry.romashlashes.test
mirror.romashlashes.test
dev.romashlashes.test
```

будут разрешаться централизованно.

### Mirror

Сейчас mirror содержит только provider:

```text
bpg/proxmox
```

Если Terraform начнёт использовать другие providers, их также потребуется зеркалировать либо изменить policy.

---

## 24. Главная идея в одном абзаце

GitLab Runner запускает Terraform не напрямую на сервере, а внутри специального Docker image `terraform-ci`. Этот image содержит правильную версию Terraform, доверяет внутренним HTTPS-сертификатам и знает, что provider `bpg/proxmox` нужно скачивать не из заблокированного публичного Registry, а с нашего `mirror-01`. Сам Docker image хранится в GitLab Container Registry. Таким образом CI стал воспроизводимым и не зависит от VPN, ручной настройки конкретного Runner или прямого доступа к `registry.terraform.io`.

---

## 25. Статус

На момент создания документации:

```text
GitLab HTTPS                         OK
GitLab Container Registry           OK
GitLab Runner HTTPS                 OK
Docker trust for Registry           OK
Terraform Provider Mirror           OK
terraform-ci:1.0.0 build            OK
terraform-ci Registry push          OK
terraform-ci Registry pull          OK
Terraform 1.16.4 inside image       OK
bpg/proxmox 0.114.0 via mirror      OK
GitLab terraform-check              OK
```

`ansible-check` требует отдельного разбора по CI job log.
