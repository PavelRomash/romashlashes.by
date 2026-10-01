# Romash Lashes — Production Go-Live Runbook

## Goal

Provide stable public availability of:

- https://romashlashes.by
- https://www.romashlashes.by

Primary priority: public website availability and safe, repeatable production deployment.

Monitoring, Grafana, centralized logging and Kubernetes remain deferred until the production deployment workflow is complete and stable.

## Current environments

| Environment | Host | IP | Status |
|---|---|---:|---|
| DEV | dev-01 | 192.168.0.185 | Running |
| STAGE | stage-01 | 192.168.0.184 | Running |
| PROD | prod-01 | 192.168.0.183 | Running / Public |

## Verified platform state

- DEV deployment via GitLab CI works.
- STAGE deployment via GitLab CI works.
- PROD application deployment via Ansible works.
- Docker Compose application works.
- Django + PostgreSQL + Nginx work.
- Internal DNS works.
- DEV and STAGE use internal TLS certificates.
- PROD uses a publicly trusted Let's Encrypt certificate.
- Public HTTPS works for both `romashlashes.by` and `www.romashlashes.by`.
- HTTP-01 validation works through the production Nginx webroot.
- Certbot renewal is managed by `certbot.timer`.
- Certbot renewal dry-run and the Nginx deploy hook have been verified.

## Production TLS architecture

DEV and STAGE TLS are managed by the internal application TLS workflow.

PROD public TLS is managed independently by the `app_acme` Ansible role.

Production ACME webroot:

```text
/opt/romashlashes/certbot/www
```

Certbot certificate lineage:

```text
/etc/letsencrypt/live/romashlashes.by/
```

Nginx certificate paths:

```text
/opt/romashlashes/nginx/certs/romashlashes.by.pem
/opt/romashlashes/nginx/certs/romashlashes.by-key.pem
```

The Certbot deploy hook installs the renewed certificate into the Nginx certificate paths, validates the Nginx configuration and reloads Nginx.

Automatic renewal is provided by:

```text
certbot.timer
```

## Production go-live plan

- [x] Inspect current public DNS for romashlashes.by
- [x] Inspect current external HTTPS failure
- [x] Verify prod-01 prerequisites
- [x] Create PROD Ansible variables
- [x] Create PROD Vault secrets
- [x] Deploy application to prod-01
- [x] Verify PROD inside LAN
- [x] Configure public TLS
- [x] Configure router/NAT for TCP 80/443
- [x] Verify public DNS
- [x] Verify site from outside LAN
- [x] Verify Let's Encrypt renewal lifecycle
- [ ] Add GitLab deploy-prod
- [ ] Document application rollback procedure
- [ ] Commit final known-good state

## TLS rollback

The mkcert certificate used immediately before the Let's Encrypt cutover was saved on `prod-01` in:

```text
/var/backups/romashlashes/tls/pre-letsencrypt-20261001T090405Z
```

The backup contains the previous certificate and private key and is retained only as a go-live rollback asset.

The normal production TLS source of truth is now:

```text
/etc/letsencrypt
```

Do not replace the Let's Encrypt certificate with the rollback certificate during normal operations.

## Deployment rollback principle

Production changes must be validated before they are considered complete.

A production deployment must preserve a known-good revision that can be redeployed if application health checks fail.

The full application rollback procedure will be documented together with the GitLab `deploy-prod` workflow.

## Deferred work

Do not start these until the production deployment workflow is complete and stable:

- Prometheus
- Grafana
- centralized logging
- Kubernetes
- additional platform improvements
