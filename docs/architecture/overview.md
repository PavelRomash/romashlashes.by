# Architecture overview

## Current state

At the moment the project runs on a single physical Proxmox host.

```mermaid
flowchart TB

    Internet((Internet))
    Router[Home Router]

    Workstation[Workstation]
    Proxmox[Proxmox VE 9.2<br/>192.168.0.176]

    Internet --> Router
    Router --> Workstation
    Router --> Proxmox
```

## Target state — phase 1

Terraform will manage virtual machines on Proxmox.

```mermaid
flowchart TB

    Internet((Internet))
    Router[Home Router]

    Workstation[Workstation<br/>Terraform / Git]
    Proxmox[Proxmox VE 9.2]

    DEV[DEV VM]
    STAGE[STAGE VM]
    PROD[PROD VM]

    Internet --> Router

    Router --> Workstation
    Router --> Proxmox

    Workstation -->|Proxmox API :8006| Proxmox

    Proxmox --> DEV
    Proxmox --> STAGE
    Proxmox --> PROD
```

## Target state — later

The environments will eventually host containerized workloads and Kubernetes.

```mermaid
flowchart TB

    Git[Git repository]
    CI[CI/CD]
    Proxmox[Proxmox]

    DEV[DEV]
    STAGE[STAGE]
    PROD[PROD]

    Git --> CI

    Proxmox --> DEV
    Proxmox --> STAGE
    Proxmox --> PROD

    CI --> DEV
    DEV --> STAGE
    STAGE --> PROD
```

This diagram represents the target architecture and not the current production state.
