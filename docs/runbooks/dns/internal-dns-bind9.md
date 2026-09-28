# Internal DNS: BIND 9 on Proxmox

## Status

Planned / implementation in progress.

## Goal

Replace host-local `/etc/hosts` records and GitLab Runner `extra_hosts` workarounds with a centralized, redundant internal DNS service managed as Infrastructure as Code.

The DNS layer must work independently of Kubernetes and must be available to:

- dev-01
- stage-01
- prod-01
- ci-01
- gitlab-01
- mirror-01
- future Kubernetes nodes
- operator workstation (macOS) through split DNS

## Target architecture

```text
                         +------------------+
                         |      dns-01      |
                         | 192.168.0.10     |
                         | BIND 9 primary   |
                         +--------+---------+
                                  |
                         NOTIFY / AXFR/IXFR
                                  |
                         +--------v---------+
                         |      dns-02      |
                         | 192.168.0.11     |
                         | BIND 9 secondary |
                         +------------------+

dev / stage / prod / ci / gitlab / mirror / future nodes
               |                    |
               +---- DNS #1 --------+
               +---- DNS #2 ----------------+
```

Both DNS servers run as Debian 13 VMs on Proxmox.

Current limitation: both DNS VMs initially run on the same physical Proxmox node. This protects against a DNS VM/service failure, but not against failure of the physical Proxmox host. When a second physical virtualization node becomes available, `dns-02` should be moved there.

## Addressing

Reserved infrastructure addresses:

| System | Address | Purpose |
|---|---:|---|
| dns-01 | 192.168.0.10 | BIND primary |
| dns-02 | 192.168.0.11 | BIND secondary |

These addresses must be excluded from the router DHCP pool before they are assigned.

Existing application/infrastructure addresses remain unchanged during the DNS migration:

| System | Address |
|---|---:|
| prod-01 | 192.168.0.183 |
| stage-01 | 192.168.0.184 |
| dev-01 | 192.168.0.185 |
| ci-01 | 192.168.0.186 |
| gitlab-01 | 192.168.0.187 |
| mirror-01 | 192.168.0.188 |

## Naming strategy

### Canonical internal zone

The long-term internal zone is:

```text
int.romashlashes.by
```

Canonical records:

```text
dns-01.int.romashlashes.by       -> 192.168.0.10
dns-02.int.romashlashes.by       -> 192.168.0.11

prod-01.int.romashlashes.by      -> 192.168.0.183
stage-01.int.romashlashes.by     -> 192.168.0.184
dev-01.int.romashlashes.by       -> 192.168.0.185
ci-01.int.romashlashes.by        -> 192.168.0.186
gitlab-01.int.romashlashes.by    -> 192.168.0.187
mirror-01.int.romashlashes.by    -> 192.168.0.188

prod.int.romashlashes.by         -> 192.168.0.183
stage.int.romashlashes.by        -> 192.168.0.184
dev.int.romashlashes.by          -> 192.168.0.185
gitlab.int.romashlashes.by       -> 192.168.0.187
registry.int.romashlashes.by     -> 192.168.0.187
mirror.int.romashlashes.by       -> 192.168.0.188
```

### Compatibility zone

Current services use names under:

```text
romashlashes.test
```

To avoid a disruptive cutover, the new DNS servers also temporarily serve this compatibility zone:

```text
gitlab.romashlashes.test         -> 192.168.0.187
registry.romashlashes.test       -> 192.168.0.187
mirror.romashlashes.test         -> 192.168.0.188
dev.romashlashes.test            -> 192.168.0.185
stage.romashlashes.test          -> 192.168.0.184
prod.romashlashes.test           -> 192.168.0.183
```

This allows the current TLS certificates, GitLab URL, Terraform mirror URL and CI configuration to continue working while `/etc/hosts` is removed.

After service certificates and URLs are migrated to `*.int.romashlashes.by`, the `romashlashes.test` compatibility zone can be removed.

## Reverse DNS

Authoritative reverse zone:

```text
0.168.192.in-addr.arpa
```

PTR records map infrastructure addresses back to canonical `int.romashlashes.by` hostnames.

## Responsibilities

### Terraform

Terraform creates `dns-01` and `dns-02` from the standard Debian 13 template.

Requirements:

- 1 vCPU each
- 512 MB RAM each
- 8 GB disk each
- static IPv4 via Cloud-Init
- QEMU guest agent enabled
- bridge `vmbr0`

Terraform must not install BIND or manage DNS records.

### Ansible

Ansible:

- installs `bind9`, `bind9-utils` and `dnsutils`;
- configures primary and secondary roles;
- configures recursive resolution for the trusted LAN;
- creates authoritative forward and reverse zones;
- restricts zone transfers to `dns-02`;
- validates BIND configuration;
- enables and starts `named.service`;
- configures existing Linux clients to use both DNS servers.

### BIND

`dns-01` stores the authoritative primary copy of the zones.

`dns-02` receives zone data from `dns-01` using DNS zone transfer and updates on NOTIFY.

For names outside internal authoritative zones, BIND forwards requests to configured upstream recursive resolvers.

## Security model

DNS service is intended for the internal network only.

Expected access policy:

```text
allow-query      -> localhost + 192.168.0.0/24
allow-recursion  -> localhost + 192.168.0.0/24
allow-transfer   -> dns-02 only
```

Both UDP/53 and TCP/53 are required.

TCP/53 is required not only for large DNS replies but also for zone transfers.

The servers do not expose an open recursive resolver to the Internet.

## BIND file layout

Primary zone files:

```text
/etc/bind/zones/
├── db.int.romashlashes.by
├── db.romashlashes.test
└── db.0.168.192
```

Secondary zone copies are stored under BIND's writable cache directory:

```text
/var/cache/bind/
```

## Primary / secondary behavior

Primary:

```text
dns-01
  |
  | zone changes
  |
  +-- NOTIFY --> dns-02
  |
  +-- AXFR/IXFR allowed only to 192.168.0.11
```

Secondary:

```text
dns-02
  |
  +-- primaries { 192.168.0.10; }
  |
  +-- serves transferred copy if dns-01 is unavailable
```

## DNS client migration

Existing Linux VMs are migrated only after both DNS servers are healthy.

Target resolver order:

```text
192.168.0.10
192.168.0.11
```

`systemd-resolved` is configured so internal DNS servers handle resolution and forward public names.

Validation on every client:

```bash
resolvectl status
getent hosts gitlab.romashlashes.test
getent hosts gitlab.int.romashlashes.by
dig gitlab.int.romashlashes.by
dig github.com
```

The migration must prove both:

1. internal resolution works;
2. external Internet DNS still works.

## macOS split DNS

The Mac should not globally use lab DNS when it is outside the lab network.

Use macOS per-domain resolver files:

```text
/etc/resolver/int.romashlashes.by
/etc/resolver/romashlashes.test
```

Each resolver file points to:

```text
nameserver 192.168.0.10
nameserver 192.168.0.11
```

This sends only the internal zones to the lab DNS servers while normal public DNS remains controlled by the active network.

## GitLab Runner migration

Current Runner `extra_hosts` entries are retained during initial DNS deployment.

After the Runner host and Docker job containers successfully resolve:

```text
gitlab.romashlashes.test
registry.romashlashes.test
mirror.romashlashes.test
```

through BIND, `extra_hosts` is removed from `/etc/gitlab-runner/config.toml`.

Validation:

```bash
sudo gitlab-runner verify
```

and from a temporary diagnostic container verify resolution of all three internal service names.

## Migration phases

### Phase 1 - network reservation

Reserve:

```text
192.168.0.10
192.168.0.11
```

outside DHCP allocation.

Confirm gateway and subnet.

### Phase 2 - Terraform

Create:

```text
dns-01
dns-02
```

with static IP addresses.

Run:

```bash
terraform fmt
terraform validate
terraform plan
terraform apply
```

No existing VM should be replaced.

### Phase 3 - Ansible DNS servers

Add both DNS hosts to inventory.

Run baseline if required, then deploy BIND:

```bash
ansible dns -m ping
ansible-playbook playbooks/dns.yml
```

### Phase 4 - authoritative tests

Test primary directly:

```bash
dig @192.168.0.10 gitlab.int.romashlashes.by A
dig @192.168.0.10 gitlab.romashlashes.test A
dig @192.168.0.10 -x 192.168.0.187
```

Test secondary directly:

```bash
dig @192.168.0.11 gitlab.int.romashlashes.by A
dig @192.168.0.11 gitlab.romashlashes.test A
dig @192.168.0.11 -x 192.168.0.187
```

Check authority:

```bash
dig @192.168.0.10 int.romashlashes.by SOA
dig @192.168.0.11 int.romashlashes.by SOA
```

The SOA serial must match.

### Phase 5 - recursive tests

```bash
dig @192.168.0.10 github.com
dig @192.168.0.11 github.com
```

Both must return public DNS answers.

### Phase 6 - client migration

Apply the DNS client role to Linux infrastructure.

Do not remove `/etc/hosts` yet.

Validate every critical service.

### Phase 7 - remove compatibility hacks

After successful validation:

- remove relevant `/etc/hosts` entries;
- remove GitLab Runner `extra_hosts`;
- rerun CI;
- verify GitLab Registry;
- verify Terraform mirror;
- verify DEV deployment.

### Phase 8 - service-name migration

Reissue internal TLS certificates for canonical names:

```text
gitlab.int.romashlashes.by
registry.int.romashlashes.by
mirror.int.romashlashes.by
```

Migrate application/configuration references one service at a time.

Only after all consumers are migrated remove the `romashlashes.test` zone.

## Zone serial policy

Use date-based serials:

```text
YYYYMMDDNN
```

Example:

```text
2026092701
```

Every authoritative zone-data change must increase the serial.

## Failure tests

### Primary failure

Stop BIND on dns-01:

```bash
sudo systemctl stop named
```

Clients should continue resolving through dns-02.

Restart after the test:

```bash
sudo systemctl start named
```

### Secondary failure

Stop BIND on dns-02.

Clients should continue resolving through dns-01.

### Physical-host limitation

If the single Proxmox host fails, both DNS VMs currently fail together.

Target future state:

```text
Proxmox node A -> dns-01
Proxmox node B -> dns-02
```

## Operational checks

Service:

```bash
systemctl status named
```

Configuration:

```bash
named-checkconf
```

Zone:

```bash
named-checkzone int.romashlashes.by   /etc/bind/zones/db.int.romashlashes.by
```

Logs:

```bash
journalctl -u named --no-pager
```

Resolver:

```bash
dig @192.168.0.10 gitlab.int.romashlashes.by
dig @192.168.0.11 gitlab.int.romashlashes.by
```

## Updating DNS records

DNS records are changed in Ansible-managed inventory/group variables or templates, not manually on the server.

Workflow:

```text
edit IaC
  -> increase zone serial
  -> ansible-lint
  -> syntax-check
  -> ansible-playbook
  -> dig primary
  -> dig secondary
  -> commit
  -> push
```

Manual edits under `/etc/bind` are configuration drift.

## Backup

The authoritative source of zone configuration is Git.

No secrets are expected in DNS zone files.

For disaster recovery:

1. Terraform recreates VM(s).
2. Ansible reinstalls/configures BIND.
3. Primary zone files are recreated from Git.
4. Secondary receives the zones from the primary.

## Production-like decisions

- DNS is independent of Kubernetes.
- Two authoritative/resolver instances are used.
- Primary/secondary replication is used.
- Static addresses are used for DNS infrastructure.
- Forward and reverse DNS are managed.
- Zone transfers are restricted.
- Recursion is restricted to the trusted LAN.
- Configuration is stored in Git and applied with Ansible.
- Existing service names are migrated without a big-bang cutover.
- `/etc/hosts` and Runner `extra_hosts` are temporary migration aids only.
