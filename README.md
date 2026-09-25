# romashlashes.by infrastructure

Production-like DevOps infrastructure project for romashlashes.by.

## Goal

Build and operate a real infrastructure for romashlashes.by while learning
modern DevOps practices and tools.

The project should use technologies only when they solve a real problem.

## Current infrastructure

- Proxmox VE 9.2
- Debian 13 Trixie
- Proxmox host: 192.168.0.176
- Single physical Proxmox host
- No production VMs yet

## Planned stack

- Proxmox VE
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

Planned persistent environments:

- DEV
- STAGE
- PROD

TEST environments may later be created dynamically by CI/CD.

## Roadmap

- [x] Install Proxmox VE
- [x] Upgrade Proxmox VE 7.4 -> 8.4
- [x] Upgrade Proxmox VE 8.4 -> 9.2
- [x] Upgrade Debian 11 -> 12 -> 13
- [ ] Create infrastructure repository
- [ ] Configure Terraform provider
- [ ] Create Proxmox API user/token
- [ ] Create first VM using Terraform
- [ ] Create Cloud-Init VM template
- [ ] Introduce Ansible
- [ ] Create DEV environment
- [ ] Create STAGE environment
- [ ] Create PROD environment
- [ ] Containerize application
- [ ] Build Kubernetes cluster
- [ ] Deploy application with Helm
- [ ] Configure CI/CD
- [ ] Introduce GitOps with Argo CD
- [ ] Deploy PostgreSQL
- [ ] Configure monitoring
- [ ] Configure centralized logging
- [ ] Configure secrets management
- [ ] Configure backup and restore
- [ ] Add analytics with ClickHouse

## Documentation

Architecture documentation is stored in:

`docs/architecture/`

Architecture decisions:

`docs/decisions/`

Operational runbooks:

`docs/runbooks/`

Troubleshooting history:

`docs/troubleshooting/`
