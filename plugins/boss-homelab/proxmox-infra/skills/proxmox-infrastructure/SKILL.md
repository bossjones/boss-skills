---
name: proxmox-infrastructure
description: Manage Proxmox VE infrastructure — VM/LXC provisioning, cloud-init templates, storage, and networking — via the proxmoxer Python library, Ansible community.general.proxmox modules, and Terraform/OpenTofu Telmate provider. Use when the user wants to provision, inspect, or modify Proxmox VMs, containers, templates, or storage; troubleshoot deployments; or generate IaC for the homelab.
---

# Proxmox Infrastructure

Single-node Proxmox VE management with LVM-thin storage, NFS backup, and cloud-init automation.

## Trigger Phrases

- "Clone the Ubuntu template to create a new VM"
- "Check storage health on the Proxmox node"
- "Create a cloud-init template from a cloud image"
- "What's the status of the Proxmox node?"
- "Deploy VMs using OpenTofu/Terraform and the Proxmox provider"
- "Troubleshoot VM deployment or networking issues"
- "Use Ansible community.general.proxmox modules"
- "Validate template configuration via the Proxmox API"
- "Manage LXC containers"

## Available Tools

Python helpers (PEP 723, run with `uv`):

- `${CLAUDE_SKILL_DIR}/tools/validate_template.py` — validate template health via Proxmox API
- `${CLAUDE_SKILL_DIR}/tools/cluster_status.py` — node health metrics and resource status
- `${CLAUDE_SKILL_DIR}/tools/check_cluster_health.py` — node diagnostics (SSH-based)
- `${CLAUDE_SKILL_DIR}/tools/check_ceph_health.py` — Ceph diagnostics

All scripts support `--help`. Invoke as:

```bash
uv run "${CLAUDE_SKILL_DIR}/tools/cluster_status.py"
```

## Core Capabilities

**Template Management**
- Ubuntu/Debian cloud-init templates with virtio-scsi
- Serial console configuration for cloud images
- Proper boot order and cloud-init CD-ROM (ide2)

**Network Infrastructure**
- Linux bridges, bridge-port mapping, optional VLAN tagging

**Storage**
- Directory, LVM-thin, and NFS pools for VM disks, backups, and ISOs

**API Automation**
- Python via `proxmoxer`
- Ansible via `community.general.proxmox_*`
- Terraform/OpenTofu via the Telmate/proxmox provider

## Quick Examples

Clone template to VM (replace IDs/IPs to match your cluster):

```bash
qm clone 9000 108 --name web-01
qm set 108 --ipconfig0 ip=192.168.2.100/24,gw=192.168.2.1
qm set 108 --net0 virtio,bridge=vmbr0
qm start 108
```

Check node health:

```bash
uv run "${CLAUDE_SKILL_DIR}/tools/cluster_status.py"
```

## For Details

- `reference/inventory.md` — current node, VMs, LXC, storage, networking snapshot
- `reference/api-reference.md` — Proxmox API authentication and endpoints
- `reference/cloud-init-patterns.md` — cloud-init template recipes
- `reference/networking.md` — bridge and VLAN patterns
- `reference/storage-management.md` — pool layout and lifecycle
- `reference/qemu-guest-agent.md` — guest agent setup
- `examples/` — Terraform/OpenTofu modules, Ansible playbooks
- `workflows/` — multi-step procedures (cluster formation, Ceph deployment)
- `anti-patterns/` — common mistakes from real deployments
