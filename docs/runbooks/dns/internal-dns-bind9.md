# Internal DNS: BIND9

## Назначение

Этот runbook описывает внутреннюю DNS-инфраструктуру проекта `romashlashes.by`.

Текущий канонический внутренний namespace:

```text
int.romashlashes.by
```

Временный namespace `romashlashes.test` выведен из эксплуатации и больше не используется runtime-конфигурацией проекта.

Внутренний DNS используется вместо:

- `/etc/hosts`;
- GitLab Runner `extra_hosts`;
- `curl --resolve`;
- ручной привязки внутренних сервисов к IP-адресам.

## Архитектура

```text
                    LAN 192.168.0.0/24
                           │
             ┌─────────────┴─────────────┐
             │                           │
         dns-01                      dns-02
      192.168.0.10                192.168.0.11
        primary                     secondary
             │                           │
             └──── TSIG zone transfer ──┘
                           │
                  int.romashlashes.by
                           │
     ┌──────────────┬──────────────┬──────────────┐
     │              │              │              │
   GitLab         Registry        Mirror          DEV
192.168.0.187   192.168.0.187  192.168.0.188  192.168.0.185
```

Оба DNS-сервера работают как:

- authoritative DNS для внутренних зон;
- recursive resolver для доверенной локальной сети;
- forwarding resolver для публичных доменов.

Текущий upstream forwarder:

```text
192.168.0.1
```

## DNS-серверы

### dns-01

```text
Hostname: dns-01
IP:       192.168.0.10
Role:     primary
```

Назначение:

- хранит primary zone files;
- является authoritative primary;
- передаёт зоны на `dns-02`;
- обслуживает recursive DNS для LAN.

### dns-02

```text
Hostname: dns-02
IP:       192.168.0.11
Role:     secondary
```

Назначение:

- получает authoritative zones через zone transfer;
- используется клиентами как второй DNS;
- обеспечивает DNS service failover при остановке `dns-01`.

Обе VM сейчас работают на одном физическом Proxmox host.

Это даёт отказоустойчивость DNS-сервиса на уровне VM, но не защищает от отказа самого Proxmox host.

## Terraform

DNS VM создаются Terraform.

Основные файлы:

```text
terraform/proxmox/dns.tf
terraform/proxmox/dns-variables.tf
terraform/proxmox/dns-outputs.tf
```

VM:

```text
dns-01 -> 192.168.0.10
dns-02 -> 192.168.0.11
```

После изменения Terraform:

```bash
cd ~/romashlashes.by/terraform/proxmox

terraform fmt -check
terraform validate
terraform plan
```

Terraform state хранится локально и не должен попадать в Git.

## Ansible

DNS configuration управляется Ansible.

Основной playbook:

```text
ansible/playbooks/dns.yml
```

Основная роль:

```text
ansible/roles/dns_bind
```

Inventory groups:

```text
dns
├── dns_primary
└── dns_secondary
```

Секрет TSIG хранится через Ansible Vault:

```text
ansible/inventory/group_vars/dns/vault.yml
```

TSIG secret нельзя хранить открытым текстом в Git.

## Canonical zone

Основная внутренняя зона:

```text
int.romashlashes.by
```

Примеры основных записей:

```text
dns-01.int.romashlashes.by     -> 192.168.0.10
dns-02.int.romashlashes.by     -> 192.168.0.11

prod-01.int.romashlashes.by    -> 192.168.0.183
stage-01.int.romashlashes.by   -> 192.168.0.184
dev-01.int.romashlashes.by     -> 192.168.0.185
ci-01.int.romashlashes.by      -> 192.168.0.186
gitlab-01.int.romashlashes.by  -> 192.168.0.187
mirror-01.int.romashlashes.by  -> 192.168.0.188
```

Service aliases:

```text
dev.int.romashlashes.by       -> 192.168.0.185
gitlab.int.romashlashes.by    -> 192.168.0.187
registry.int.romashlashes.by  -> 192.168.0.187
mirror.int.romashlashes.by    -> 192.168.0.188
```

## Reverse zone

Reverse DNS zone:

```text
0.168.192.in-addr.arpa
```

Пример:

```text
192.168.0.187
  ->
gitlab-01.int.romashlashes.by
```

Проверка:

```bash
dig @192.168.0.10 -x 192.168.0.187 +short
dig @192.168.0.11 -x 192.168.0.187 +short
```

Ожидается:

```text
gitlab-01.int.romashlashes.by.
```

## Primary / secondary

`dns-01` является primary.

`dns-02` является secondary.

Передача зон защищена TSIG.

Схема:

```text
dns-01
 primary
   │
   │ TSIG-authenticated AXFR/IXFR
   ▼
dns-02
 secondary
```

На primary zone files хранятся в:

```text
/etc/bind/zones/
```

На secondary полученные зоны хранятся BIND в cache directory.

## Проверка authoritative DNS

Проверка GitLab через primary:

```bash
dig @192.168.0.10 gitlab.int.romashlashes.by A +short
```

Проверка через secondary:

```bash
dig @192.168.0.11 gitlab.int.romashlashes.by A +short
```

Ожидается:

```text
gitlab-01.int.romashlashes.by.
192.168.0.187
```

Registry:

```bash
dig @192.168.0.10 registry.int.romashlashes.by A +short
```

Mirror:

```bash
dig @192.168.0.10 mirror.int.romashlashes.by A +short
```

DEV:

```bash
dig @192.168.0.10 dev.int.romashlashes.by A +short
```

## Проверка SOA

Primary:

```bash
dig @192.168.0.10 int.romashlashes.by SOA +short
```

Secondary:

```bash
dig @192.168.0.11 int.romashlashes.by SOA +short
```

SOA serial должен совпадать на обоих серверах.

После изменения zone data serial должен быть увеличен.

## Recursive DNS

Оба сервера разрешают публичные DNS-имена для доверенной LAN.

Проверка:

```bash
dig @192.168.0.10 deb.debian.org A +short
dig @192.168.0.11 deb.debian.org A +short
```

Оба запроса должны возвращать публичные IP.

## DNS clients

Основные Debian VM используют:

- Netplan;
- systemd-networkd;
- systemd-resolved.

Ansible role:

```text
ansible/roles/dns_client
```

Роль создаёт:

```text
/etc/netplan/60-internal-dns.yaml
```

Исходный cloud-init Netplan file не изменяется:

```text
/etc/netplan/50-cloud-init.yaml
```

Основные DNS client settings:

```text
DNS:
  192.168.0.10
  192.168.0.11

Search domain:
  int.romashlashes.by
```

DHCP продолжает использоваться для IP и gateway, но DNS, полученный через DHCP, отключён.

Проверка на Debian client:

```bash
resolvectl status
```

Проверка имени:

```bash
getent ahostsv4 gitlab.int.romashlashes.by
```

## Docker DNS

Docker workloads используют внутренние DNS-серверы:

```text
192.168.0.10
192.168.0.11
```

Это позволяет контейнерам использовать canonical service names без `extra_hosts`.

## GitLab Runner

GitLab Runner на `ci-01` больше не использует `extra_hosts` для GitLab.

Runner подключается к:

```text
https://gitlab.int.romashlashes.by
```

Проверка:

```bash
sudo gitlab-runner verify
```

## macOS client

На Mac используется split DNS через `/etc/resolver`.

Canonical resolver:

```text
/etc/resolver/int.romashlashes.by
```

Содержимое:

```text
nameserver 192.168.0.10
nameserver 192.168.0.11
```

Проверка:

```bash
dscacheutil -q host -a name gitlab.int.romashlashes.by
```

После изменений DNS cache:

```bash
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

Временный resolver для `romashlashes.test` удалён.

## Failover

Клиенты настроены на два DNS-сервера:

```text
192.168.0.10
192.168.0.11
```

Проверенный сценарий:

```text
dns-01 stopped
      ↓
systemd-resolved
      ↓
dns-02
      ↓
internal DNS works
public recursion works
Docker DNS works
```

Для теста:

```bash
sudo systemctl stop named
```

На клиенте:

```bash
resolvectl status
getent ahostsv4 gitlab.int.romashlashes.by
getent ahostsv4 deb.debian.org
```

После теста:

```bash
sudo systemctl start named
```

## Применение DNS role

Перед применением:

```bash
cd ~/romashlashes.by/ansible
ansible-lint
```

Syntax check:

```bash
ansible-playbook \
  -i inventory/hosts.yml \
  playbooks/dns.yml \
  --syntax-check \
  --ask-vault-pass
```

Применение:

```bash
ansible-playbook \
  -i inventory/hosts.yml \
  playbooks/dns.yml \
  --ask-vault-pass
```

## Health checks внутренних сервисов

GitLab:

```bash
curl -I https://gitlab.int.romashlashes.by/
```

Нормальный ответ:

```text
HTTP 302
```

Registry:

```bash
curl -I https://registry.int.romashlashes.by/v2/
```

Нормальный ответ без авторизации:

```text
HTTP 401
```

Registry authentication realm должен указывать на:

```text
https://gitlab.int.romashlashes.by/jwt/auth
```

Terraform mirror:

```bash
curl -fsS https://mirror.int.romashlashes.by/healthz
```

Ожидается:

```text
ok
```

DEV:

```bash
curl -I https://dev.int.romashlashes.by/
```

Ожидается:

```text
HTTP 200
```

## TLS и DNS

Canonical DNS names:

```text
gitlab.int.romashlashes.by
registry.int.romashlashes.by
mirror.int.romashlashes.by
dev.int.romashlashes.by
```

Проверка SAN:

```bash
echo | openssl s_client \
  -connect gitlab.int.romashlashes.by:443 \
  -servername gitlab.int.romashlashes.by \
  2>/dev/null |
openssl x509 -noout -ext subjectAltName
```

## История миграции namespace

Изначально инфраструктура использовала временный namespace:

```text
romashlashes.test
```

После внедрения централизованного BIND DNS был введён canonical namespace:

```text
int.romashlashes.by
```

Миграция выполнялась по схеме:

```text
создать canonical DNS
        ↓
создать transition TLS certificates
        ↓
перевести GitLab
        ↓
перевести Registry
        ↓
перевести Runner
        ↓
перевести Terraform mirror
        ↓
перевести DEV
        ↓
проверить CI/CD
        ↓
удалить compatibility DNS
        ↓
удалить old SAN
```

После завершения миграции `romashlashes.test` больше не является active DNS zone.

Проверка:

```bash
dig @192.168.0.10 gitlab.romashlashes.test A +short
dig @192.168.0.11 gitlab.romashlashes.test A +short
```

Ожидаемый результат:

```text
<пусто>
```

## Troubleshooting

BIND status:

```bash
sudo systemctl status named
```

Logs:

```bash
sudo journalctl -u named -n 100 --no-pager
```

Проверка конфигурации:

```bash
sudo /usr/bin/named-checkconf /etc/bind/named.conf
```

Проверка canonical zone на primary:

```bash
sudo /usr/bin/named-checkzone \
  int.romashlashes.by \
  /etc/bind/zones/db.int.romashlashes.by
```

Проверка порта 53:

```bash
sudo ss -lntup | grep ':53'
```

Проверка клиента:

```bash
resolvectl status
getent ahostsv4 gitlab.int.romashlashes.by
```

Очистка cache:

```bash
sudo resolvectl flush-caches
```

## Recovery

Если `dns-01` недоступен, клиенты должны использовать:

```text
192.168.0.11
```

Если `dns-02` недоступен, основной DNS работает через:

```text
192.168.0.10
```

Если оба DNS недоступны, внутренние service names перестанут разрешаться.

После восстановления проверить:

```bash
dig @192.168.0.10 gitlab.int.romashlashes.by A +short
```

или:

```bash
dig @192.168.0.11 gitlab.int.romashlashes.by A +short
```

## Security

TSIG secret:

- хранится через Ansible Vault;
- не выводится в терминал;
- не хранится открытым текстом в Git;
- используется для zone transfer между primary и secondary.

TLS private keys:

- не должны храниться в открытом Git repository;
- локальные secret files исключаются из Git;
- дальнейшая цель — централизованное управление через Vault/PKI.

Recursive DNS должен быть доступен только доверенной сети.

## Ограничения текущей архитектуры

`dns-01` и `dns-02` находятся на одном физическом Proxmox host.

Текущая схема защищает от:

- остановки BIND;
- сбоя одной DNS VM;
- ошибки отдельной VM.

Но не защищает от:

- отказа Proxmox host;
- отказа питания;
- отказа физической сети этого host.

В будущем secondary DNS можно вынести на другой физический узел.

## Финальная проверка

Canonical DNS:

```bash
for dns in 192.168.0.10 192.168.0.11; do
  echo "=== $dns ==="
  dig @"$dns" gitlab.int.romashlashes.by A +short
  dig @"$dns" registry.int.romashlashes.by A +short
  dig @"$dns" mirror.int.romashlashes.by A +short
  dig @"$dns" dev.int.romashlashes.by A +short
done
```

Public recursion:

```bash
dig @192.168.0.10 deb.debian.org A +short
dig @192.168.0.11 deb.debian.org A +short
```

Reverse DNS:

```bash
dig @192.168.0.10 -x 192.168.0.187 +short
dig @192.168.0.11 -x 192.168.0.187 +short
```

Retired namespace:

```bash
dig @192.168.0.10 gitlab.romashlashes.test A +short
dig @192.168.0.11 gitlab.romashlashes.test A +short
```

Для retired namespace результат должен быть пустым.

После DNS-проверок:

```bash
curl -I https://gitlab.int.romashlashes.by/
curl -I https://registry.int.romashlashes.by/v2/
curl -fsS https://mirror.int.romashlashes.by/healthz
curl -I https://dev.int.romashlashes.by/
```

После успешных проверок инфраструктура считается работающей на canonical namespace `int.romashlashes.by`.
