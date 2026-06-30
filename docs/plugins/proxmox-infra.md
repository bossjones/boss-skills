# proxmox-infra

> `boss-homelab` · v0.1.1 · [plugin source](../../plugins/boss-homelab/proxmox-infra/)

Homelab Proxmox VE tooling for Claude Code: a single comprehensive skill for managing
nodes, VMs, LXC containers, storage, and networking via the
[proxmoxer](https://github.com/proxmoxer/proxmoxer) Python library, Ansible
(`community.general.proxmox`), and Terraform/OpenTofu (the Telmate provider).

## Installation

```bash
/plugin marketplace add bossjones/boss-skills   # once
/plugin install proxmox-infra@boss-skills
```

## Skills

| Skill | Description |
|-------|-------------|
| `proxmox-infrastructure` | Manage Proxmox VE infrastructure — VM/LXC provisioning, cloud-init templates, storage, and networking. Use to provision, inspect, or modify VMs, containers, templates, or storage; troubleshoot deployments; or generate IaC for the homelab. |

## Bundled resources

The skill is more than a single `SKILL.md` — it carries reference material, runnable
helpers, multi-step workflows, and a worked example.

### Helper scripts (`tools/`)

| Script | Purpose |
|--------|---------|
| `cluster_status.py` | Report overall cluster status. |
| `check_cluster_health.py` | Health check across cluster nodes. |
| `check_ceph_health.py` | Health check for the Ceph storage cluster. |
| `validate_template.py` | Validate a VM template before cloning from it. |

### Reference docs (`reference/`)

| Document | Topic |
|----------|-------|
| `api-reference.md` | proxmoxer API usage |
| `cloud-init-patterns.md` | cloud-init template patterns |
| `networking.md` | Bridge, VLAN, and bonding configuration |
| `storage-management.md` | Storage pools and volumes |
| `qemu-guest-agent.md` | QEMU guest agent setup |
| `inventory.md` | Homelab inventory reference |

### Workflows (`workflows/`)

| Workflow | Procedure |
|----------|-----------|
| `cluster-formation.md` | Form a multi-node Proxmox cluster |
| `ceph-deployment.md` | Deploy Ceph distributed storage |

The skill also includes an `anti-patterns/common-mistakes.md` guide and a worked
`examples/01-basic-vm/` deployment.

## Usage examples

### Provision a VM from a cloud-init template

```text
Provision a new Ubuntu VM on Proxmox from a cloud-init template with 4 GB RAM and 2 vCPUs.
```

The skill consults `reference/cloud-init-patterns.md`, validates the template with
`tools/validate_template.py`, and provisions the VM through `proxmoxer`.

### Inspect cluster health

```text
Check the health of my Proxmox cluster and the Ceph storage.
```

The skill runs `tools/cluster_status.py`, `tools/check_cluster_health.py`, and
`tools/check_ceph_health.py`, then summarizes node and storage status.

### Generate Infrastructure as Code

```text
Generate Terraform for the homelab using the Telmate Proxmox provider for two LXC containers.
```

The skill produces Terraform/OpenTofu configuration following the patterns in its reference
docs, ready to `terraform plan`.

## Status

Single-node setup (`pve1`). Tools are verified against the Proxmox API via `proxmoxer` and
over SSH.

## See also

- Plugin source: [`plugins/boss-homelab/proxmox-infra/`](../../plugins/boss-homelab/proxmox-infra/)
- Plugin README: [`plugins/boss-homelab/proxmox-infra/README.md`](../../plugins/boss-homelab/proxmox-infra/README.md)
