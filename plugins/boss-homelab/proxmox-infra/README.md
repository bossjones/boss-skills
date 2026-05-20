# proxmox-infra

Homelab Proxmox VE tooling for Claude Code: skills for managing nodes, VMs, LXC containers, storage, and
networking via the proxmoxer Python library, Ansible (`community.general.proxmox`), and Terraform/OpenTofu
(Telmate provider).

## Installation

```bash
/plugin install proxmox-infra@boss-skills
```

## Components

### Skills

- **proxmox-infrastructure** — VM/LXC provisioning, cloud-init templates, storage, and networking.
  Bundles Python helpers under `tools/`, recipe references under `reference/`, working `examples/`,
  and multi-step `workflows/`.

## Status

Single-node setup (pve1). Tools verified via the Proxmox API (`proxmoxer`) and over SSH.
