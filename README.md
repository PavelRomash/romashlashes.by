# romashlashes.by infrastructure

Production-like DevOps infrastructure project for `romashlashes.by`.

## Goal

Build and operate real infrastructure for `romashlashes.by` while learning modern DevOps practices and tools.

Technologies are introduced only when they solve a real infrastructure or operational problem.

## Current infrastructure

- Proxmox VE 9.2
- Debian 13 Trixie
- Single physical Proxmox host
- Proxmox host: `192.168.0.176`

Current Proxmox templates:

- `9000` — raw Debian 13 GenericCloud template
- `9001` — Debian 13 template prepared manually
- `9100` — Debian 13 template built automatically with Packer

Current Terraform-managed environments:

- `dev-01`
- `stage-01`
- `prod-01`

All environment VMs are created from template `9100`.

Each VM currently uses:

- Debian 13
- Cloud-Init
- QEMU Guest Agent
- SSH key authentication
- DHCP networking

Terraform automatically receives VM IPv4 addresses through QEMU Guest Agent.

## Current provisioning flow

```text
Debian 13 GenericCloud
        ↓
Template 9000
        ↓
      Packer
        ↓
Template 9100
        ↓
    Terraform
        ↓
 ┌──────┼───────┐
 ↓      ↓       ↓
DEV   STAGE    PROD
```

Current responsibility split:

```text
Packer
→ builds the reusable VM template

Terraform
→ creates and manages infrastructure

Cloud-Init
→ performs first-boot configuration

QEMU Guest Agent
→ provides guest information to Proxmox and Terraform

SSH
→ provides administrative access
```

The next configuration layer will be:

```text
Ansible
→ configures operating systems and installed software
```

## Planned stack

- Proxmox VE
- Packer
- Terraform
- Ansible
- Docker
- Kubernetes
- Helm
- GitLab CI/CD
- Argo CD
- HashiCorp Vault
- Prometheus
- Grafana
- Alertmanager
- Loki
- OpenTelemetry
- PostgreSQL
- ClickHouse
- Redis
- Nginx / Ingress
- Bash
- Python
- Backup / Restore

## Environments

Persistent environments:

- DEV
- STAGE
- PROD

Current VMs:

```text
dev-01
stage-01
prod-01
```

TEST environments may later be created dynamically by CI/CD.

## Roadmap

### Platform foundation

- [x] Install Proxmox VE
- [x] Upgrade Proxmox VE 7.4 -> 8.4
- [x] Upgrade Proxmox VE 8.4 -> 9.2
- [x] Upgrade Debian 11 -> 12 -> 13
- [x] Create infrastructure repository

### VM image automation

- [x] Create Debian 13 Cloud-Init template manually
- [x] Install and configure QEMU Guest Agent
- [x] Introduce Packer
- [x] Automate Debian 13 template creation with Packer
- [x] Validate Packer template with Terraform

### Infrastructure as Code

- [x] Configure Proxmox API user/token
- [x] Configure Terraform provider
- [x] Create first VM using Terraform
- [x] Create DEV environment
- [x] Create STAGE environment
- [x] Create PROD environment
- [x] Verify SSH access to all environments

### Configuration management

- [ ] Introduce Ansible
- [ ] Create Ansible inventory for DEV / STAGE / PROD
- [ ] Configure baseline OS settings with Ansible
- [ ] Install common system packages
- [ ] Automate server configuration

### Containers and orchestration

- [ ] Install container runtime
- [ ] Containerize application
- [ ] Build Kubernetes cluster
- [ ] Deploy application with Helm

### Delivery and GitOps

- [ ] Configure CI/CD
- [ ] Introduce GitOps with Argo CD

### Data services

- [ ] Deploy PostgreSQL
- [ ] Introduce Redis where required
- [ ] Add analytics with ClickHouse

### Observability

- [ ] Configure Prometheus
- [ ] Configure Grafana
- [ ] Configure Alertmanager
- [ ] Configure centralized logging with Loki
- [ ] Introduce OpenTelemetry

### Security and operations

- [ ] Configure secrets management
- [ ] Configure backup and restore
- [ ] Test disaster recovery

## Documentation

Architecture documentation:

`docs/architecture/`

Architecture decisions:

`docs/decisions/`

Operational runbooks:

`docs/runbooks/`

Proxmox template runbooks:

`docs/runbooks/proxmox.template/`

Terraform runbooks:

`docs/runbooks/terraform/`

Troubleshooting history:

`docs/troubleshooting/`