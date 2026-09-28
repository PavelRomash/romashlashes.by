# Internal DNS Runbook — romashlashes.by

## 1. Назначение

Этот документ описывает внутреннюю DNS-инфраструктуру проекта `romashlashes.by`: архитектуру, Terraform, Ansible, BIND9, primary/secondary, TSIG, клиентскую конфигурацию, failover, проверки, эксплуатацию и дальнейшую миграцию с временного namespace `romashlashes.test` на канонический `int.romashlashes.by`.

Цель проекта — отказаться от локальных `/etc/hosts` и `GitLab Runner extra_hosts` и заменить их централизованным, воспроизводимым и отказоустойчивым DNS.

## 2. Архитектура

DNS-серверы:

| Host | Role | IP |
|---|---|---|
| `dns-01` | BIND primary | `192.168.0.10` |
| `dns-02` | BIND secondary | `192.168.0.11` |

Клиенты:

| Host | IP |
|---|---|
| `prod-01` | `192.168.0.183` |
| `stage-01` | `192.168.0.184` |
| `dev-01` | `192.168.0.185` |
| `ci-01` | `192.168.0.186` |
| `gitlab-01` | `192.168.0.187` |
| `mirror-01` | `192.168.0.188` |

Клиентская схема:

```text
application
   |
   v
127.0.0.53
systemd-resolved
   |
   +----------------------+
   |                      |
   v                      v
192.168.0.10          192.168.0.11
dns-01 primary        dns-02 secondary
```

Оба DNS сейчас находятся на одном физическом Proxmox-хосте. Это защищает от отказа отдельной VM или BIND, но не от отказа самого Proxmox-хоста. В будущем `dns-02` желательно перенести на второй Proxmox node.

## 3. DNS zones

### 3.1 Каноническая зона

```text
int.romashlashes.by
```

Основные A-записи:

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

Сервисные CNAME:

```text
gitlab.int.romashlashes.by
    -> gitlab-01.int.romashlashes.by

registry.int.romashlashes.by
    -> gitlab-01.int.romashlashes.by

mirror.int.romashlashes.by
    -> mirror-01.int.romashlashes.by
```

Так сервисное имя отделено от имени VM.

### 3.2 Compatibility zone

```text
romashlashes.test
```

Она оставлена временно, чтобы не ломать текущие URL и TLS-сертификаты:

```text
gitlab.romashlashes.test   -> 192.168.0.187
registry.romashlashes.test -> 192.168.0.187
mirror.romashlashes.test   -> 192.168.0.188
```

Удалять эту зону можно только после полной миграции сервисов и сертификатов на `*.int.romashlashes.by`.

### 3.3 Reverse zone

```text
0.168.192.in-addr.arpa
```

Пример:

```text
192.168.0.187
    -> gitlab-01.int.romashlashes.by.
```

Проверка:

```bash
dig @192.168.0.10 -x 192.168.0.187 +short
dig @192.168.0.11 -x 192.168.0.187 +short
```

## 4. Primary / Secondary

`dns-01` — источник истины для зон.

`dns-02` — secondary, получает зоны с primary.

```text
dns-01
primary
   |
   | NOTIFY / AXFR / IXFR
   | TSIG authenticated
   v
dns-02
secondary
```

Secondary продолжает обслуживать зоны, если BIND на primary недоступен.

## 5. TSIG

Zone transfer защищён TSIG.

Секрет хранится только в Ansible Vault:

```text
ansible/inventory/group_vars/dns/vault.yml
```

Формат:

```yaml
dns_bind_tsig_secret: !vault |
  $ANSIBLE_VAULT;1.1;AES256
  ...
```

Plaintext TSIG secret нельзя хранить в Git.

## 6. Terraform

DNS VM описаны в:

```text
terraform/proxmox/
├── dns.tf
├── dns-variables.tf
└── dns-outputs.tf
```

Параметры:

```text
dns-01: 1 CPU / 512 MB / 20 GB / 192.168.0.10/24
dns-02: 1 CPU / 512 MB / 20 GB / 192.168.0.11/24
gateway: 192.168.0.1
bootstrap DNS: 192.168.0.1
template: VM 9100
```

Перед apply:

```bash
cd ~/romashlashes.by/terraform/proxmox
terraform fmt -check
terraform validate
terraform plan
```

Terraform state не хранится в Git.

## 7. Ansible layout

```text
ansible/
├── inventory/
│   ├── hosts.yml
│   └── group_vars/
│       └── dns/
│           ├── main.yml
│           ├── vault.yml
│           └── vault.yml.example
├── playbooks/
│   ├── dns.yml
│   ├── dns-client-ci.yml
│   └── dns-client-all.yml
└── roles/
    ├── dns_bind/
    │   ├── defaults/main.yml
    │   ├── handlers/main.yml
    │   ├── tasks/main.yml
    │   └── templates/
    │       ├── named.conf.options.j2
    │       ├── named.conf.local.j2
    │       ├── dns-xfr.key.j2
    │       ├── db.int.romashlashes.by.j2
    │       ├── db.romashlashes.test.j2
    │       └── db.0.168.192.j2
    └── dns_client/
        ├── defaults/main.yml
        ├── handlers/main.yml
        ├── tasks/main.yml
        └── templates/60-internal-dns.yaml.j2
```

## 8. Inventory

DNS-группы:

```yaml
dns:
  children:
    dns_primary:
      hosts:
        dns-01:
          ansible_host: 192.168.0.10
          dns_bind_server_role: primary

    dns_secondary:
      hosts:
        dns-02:
          ansible_host: 192.168.0.11
          dns_bind_server_role: secondary
```

## 9. Что делает роль `dns_bind`

Роль:

1. валидирует роль primary/secondary;
2. устанавливает BIND;
3. создаёт директории;
4. разворачивает TSIG;
5. рендерит `named.conf.options`;
6. рендерит зоны на primary;
7. рендерит `named.conf.local`;
8. запускает `named-checkconf`;
9. запускает `named-checkzone`;
10. включает и стартует BIND;
11. проверяет внутреннюю authoritative lookup;
12. проверяет public recursive lookup.

На Debian 13 утилиты находятся здесь:

```text
/usr/bin/named-checkconf
/usr/bin/named-checkzone
```

## 10. Recursive DNS

BIND обслуживает две категории запросов.

Внутренние:

```text
gitlab.int.romashlashes.by
    -> authoritative answer from local zone
```

Публичные:

```text
github.com
    -> forwarder
    -> 192.168.0.1
```

Разрешённая сеть:

```text
192.168.0.0/24
```

Нельзя превращать сервер в открытый Internet recursive resolver.

## 11. Deploy DNS servers

```bash
cd ~/romashlashes.by/ansible
ansible-lint
```

```bash
ansible-playbook   -i inventory/hosts.yml   playbooks/dns.yml   --syntax-check   --ask-vault-pass
```

```bash
ansible-playbook   -i inventory/hosts.yml   playbooks/dns.yml   --ask-vault-pass
```

Ожидается:

```text
dns-01 ... failed=0
dns-02 ... failed=0
```

Повторный запуск должен быть идемпотентным.

## 12. SOA serial

Формат:

```text
YYYYMMDDNN
```

Пример:

```text
2026092701
```

При каждом изменении зоны serial должен увеличиваться.

Примеры:

```text
2026092801
2026092802
```

Если serial не изменить, secondary может не принять новую версию зоны.

## 13. Проверка DNS servers

Canonical:

```bash
dig @192.168.0.10 gitlab.int.romashlashes.by A
dig @192.168.0.11 gitlab.int.romashlashes.by A
```

Compatibility:

```bash
dig @192.168.0.10 gitlab.romashlashes.test A +short
dig @192.168.0.11 gitlab.romashlashes.test A +short
```

Reverse:

```bash
dig @192.168.0.10 -x 192.168.0.187 +short
dig @192.168.0.11 -x 192.168.0.187 +short
```

Public:

```bash
dig @192.168.0.10 github.com A +short
dig @192.168.0.11 github.com A +short
```

SOA:

```bash
dig @192.168.0.10 int.romashlashes.by SOA +short
dig @192.168.0.11 int.romashlashes.by SOA +short
```

Serial должен совпадать на обоих серверах.

Проверенный serial при первоначальном развёртывании:

```text
2026092701
```

## 14. DNS clients

Клиенты используют Netplan + `systemd-networkd` + `systemd-resolved`.

Cloud-Init владеет:

```text
/etc/netplan/50-cloud-init.yaml
```

Ansible его не редактирует.

Роль `dns_client` создаёт:

```text
/etc/netplan/60-internal-dns.yaml
```

Override:

```yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4-overrides:
        use-dns: false
      nameservers:
        addresses:
          - 192.168.0.10
          - 192.168.0.11
        search:
          - int.romashlashes.by
```

DHCP продолжает выдавать IP и gateway, но DNS от DHCP игнорируется.

Проверка:

```bash
resolvectl status
```

Ожидается:

```text
Current DNS Server: 192.168.0.10
DNS Servers: 192.168.0.10 192.168.0.11
DNS Domain: int.romashlashes.by
```

## 15. Canary rollout

Первым клиентом был `ci-01`.

Причина: именно GitLab Runner ранее ломался при отсутствии ручного hostname mapping.

Порядок:

```text
DNS servers
   |
   v
ci-01
   |
   +--> host DNS
   +--> GitLab Runner
   +--> Docker DNS
   +--> failover
   |
   v
remaining VMs
```

Canary:

```bash
ansible-playbook   -i inventory/hosts.yml   playbooks/dns-client-ci.yml   --ask-vault-pass
```

## 16. Full rollout

После canary роль была применена к:

```text
dev-01
stage-01
prod-01
ci-01
gitlab-01
mirror-01
```

В playbook используется:

```yaml
serial: 1
```

Это важно для сетевых изменений: хосты изменяются по одному.

```bash
ansible-playbook   -i inventory/hosts.yml   playbooks/dns-client-all.yml   --ask-vault-pass
```

Проверенный результат:

```text
ci-01       changed=0 failed=0
dev-01      changed=2 failed=0
stage-01    changed=2 failed=0
prod-01     changed=2 failed=0
gitlab-01   changed=2 failed=0
mirror-01   changed=2 failed=0
```

## 17. Docker DNS

На `ci-01` проверено:

```bash
sudo docker run --rm busybox:1.37   nslookup gitlab.romashlashes.test
```

Docker показал:

```text
Server: 192.168.0.10
```

И успешно получил:

```text
gitlab.romashlashes.test -> 192.168.0.187
```

Проверены также:

```text
mirror.romashlashes.test   -> 192.168.0.188
registry.romashlashes.test -> 192.168.0.187
gitlab.int.romashlashes.by -> 192.168.0.187
```

Это особенно важно, потому что GitLab CI jobs выполняются в Docker executor.

## 18. GitLab Runner

Ранее Runner использовал:

```toml
extra_hosts = [
  "gitlab.romashlashes.test:192.168.0.187",
  "mirror.romashlashes.test:192.168.0.188"
]
```

После проверки DNS этот workaround был удалён.

Проверка:

```bash
sudo gitlab-runner verify
```

Результат:

```text
Verifying runner... is valid
```

После удаления `extra_hosts` GitLab pipeline прошёл без ошибок.

## 19. `/etc/hosts`

Были удалены записи:

```text
192.168.0.187 gitlab.romashlashes.test registry.romashlashes.test
192.168.0.188 mirror.romashlashes.test
```

После fleet-wide проверки старых service-discovery записей не осталось.

`/etc/hosts` больше не используется как механизм обнаружения внутренних сервисов.

## 20. Failover

Primary был остановлен:

```bash
ssh pavel@192.168.0.10   'sudo systemctl stop named'
```

После очистки cache:

```bash
sudo resolvectl flush-caches
```

`ci-01` переключился на:

```text
Current DNS Server: 192.168.0.11
```

Docker тоже успешно использовал:

```text
Server: 192.168.0.11
```

Проверены:

```text
gitlab.int.romashlashes.by
github.com
```

После теста primary возвращён:

```bash
ssh pavel@192.168.0.10   'sudo systemctl start named'
```

Таким образом service-level failover подтверждён.

## 21. CI/CD validation

DNS-конфигурация хранится в Git.

Проверяются:

```text
ansible-lint
Ansible syntax-check
Terraform validation
```

После реализации:

```text
GitLab pipeline: passed
GitLab push: done
GitHub push: done
```

## 22. Процедура изменения DNS record

1. Изменить нужный zone template.
2. Увеличить SOA serial.
3. Запустить `ansible-lint`.
4. Запустить syntax-check.
5. Применить `dns.yml`.
6. Проверить primary.
7. Проверить secondary.
8. Сравнить SOA serial.
9. Проверить lookup с клиента.
10. Commit / push только после runtime validation.

Пример:

```bash
cd ~/romashlashes.by/ansible

ansible-lint

ansible-playbook   -i inventory/hosts.yml   playbooks/dns.yml   --syntax-check   --ask-vault-pass

ansible-playbook   -i inventory/hosts.yml   playbooks/dns.yml   --ask-vault-pass
```

## 23. Добавление новой VM

Для нового infrastructure host:

1. создать VM через Terraform;
2. назначить стабильный IP;
3. добавить A record;
4. добавить service CNAME при необходимости;
5. добавить PTR;
6. увеличить SOA serial;
7. применить `dns.yml`;
8. добавить host в Ansible inventory;
9. применить `dns_client`;
10. проверить internal/public DNS.

## 24. Troubleshooting

BIND:

```bash
sudo systemctl status named --no-pager
```

Config:

```bash
sudo /usr/bin/named-checkconf
```

Zone:

```bash
sudo /usr/bin/named-checkzone   int.romashlashes.by   /etc/bind/zones/db.int.romashlashes.by
```

Primary:

```bash
dig @192.168.0.10 gitlab.int.romashlashes.by A
```

Secondary:

```bash
dig @192.168.0.11 gitlab.int.romashlashes.by A
```

SOA:

```bash
dig @192.168.0.10 int.romashlashes.by SOA +short
dig @192.168.0.11 int.romashlashes.by SOA +short
```

Client:

```bash
resolvectl status
```

Cache:

```bash
sudo resolvectl flush-caches
```

OS resolver:

```bash
getent hosts gitlab.int.romashlashes.by
```

Docker:

```bash
sudo docker run --rm busybox:1.37   nslookup gitlab.int.romashlashes.by
```

Runner:

```bash
sudo gitlab-runner verify
```

## 25. Recovery

### dns-01 unavailable

Clients должны использовать `192.168.0.11`.

Проверить:

```bash
dig @192.168.0.11 int.romashlashes.by SOA
```

После восстановления primary:

```bash
ansible-playbook   -i inventory/hosts.yml   playbooks/dns.yml   --ask-vault-pass
```

### dns-02 unavailable

Primary продолжает обслуживать DNS.

После восстановления secondary повторный `dns.yml` должен вернуть конфигурацию и transfer.

### Оба DNS недоступны

Так как обе VM пока на одном Proxmox host, physical host failure может отключить обе.

Приоритет восстановления:

1. Proxmox;
2. `dns-01`;
3. BIND primary;
4. authoritative/public DNS;
5. `dns-02`;
6. zone transfer;
7. clients.

## 26. Security

Не хранить в Git:

```text
plaintext TSIG
Ansible Vault password
private CA key
GitLab Runner token
Proxmox API token
Terraform state
```

Recursion разрешать только доверенной LAN.

Zone transfers — только secondary и только с TSIG.

## 27. DHCP / IP

Адреса:

```text
192.168.0.10
192.168.0.11
```

не должны выдаваться другим устройствам.

Они должны быть либо вне DHCP pool, либо зарезервированы.

## 28. Ограничения текущей схемы

1. Оба DNS находятся на одном Proxmox host.
2. Public forwarding зависит от `192.168.0.1`.
3. Compatibility namespace `romashlashes.test` всё ещё нужен части сервисов и сертификатов.

## 29. Следующий этап — TLS и canonical namespace

Целевые имена:

```text
gitlab.int.romashlashes.by
registry.int.romashlashes.by
mirror.int.romashlashes.by
```

Рекомендуемый порядок:

1. выпустить TLS certificates для canonical names;
2. перевести GitLab;
3. перевести Registry;
4. перевести Terraform mirror;
5. обновить GitLab Runner;
6. обновить Docker trust paths;
7. обновить Terraform network mirror;
8. обновить GitLab CI configuration;
9. прогнать полный pipeline;
10. найти оставшиеся `.test` references;
11. удалить compatibility zone только после полной миграции.

## 30. Финальное подтверждённое состояние

```text
dns-01 primary                 OK
dns-02 secondary               OK
TSIG zone transfer             OK
canonical zone                 OK
compatibility zone             OK
reverse DNS                    OK
public recursive DNS           OK
SOA synchronization            OK
client rollout                 OK
systemd-resolved integration   OK
Docker DNS                     OK
GitLab Runner DNS              OK
primary -> secondary failover  OK
/etc/hosts dependency removed  OK
Runner extra_hosts removed     OK
Ansible lint                   OK
Ansible syntax checks          OK
GitLab pipeline                OK
GitLab push                    OK
GitHub push                    OK
```

## 31. Общий принцип эксплуатации

```text
Git
 |
 v
Terraform + Ansible
 |
 v
Infrastructure
```

Ручные изменения допустимы только для диагностики и аварийного восстановления.

Любое постоянное изменение должно быть возвращено в Terraform или Ansible и закоммичено в репозиторий.
