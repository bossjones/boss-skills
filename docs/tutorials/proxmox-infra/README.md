# Tutorial: Provision a Proxmox VM from a cloud-init template

`proxmox-infra` ships one comprehensive skill, `proxmox-infrastructure`, for managing a Proxmox VE
homelab — VMs, LXC containers, storage, and networking — via `proxmoxer`, Ansible, and
Terraform/OpenTofu. This walkthrough provisions a single VM by cloning a cloud-init template.

**Time:** ~15 minutes · **Level:** intermediate · **Reference:** [proxmox-infra.md](../../plugins/proxmox-infra.md)

## Prerequisites

| You need | Notes |
|----------|-------|
| The plugin | `/plugin install proxmox-infra@boss-skills` |
| A reachable Proxmox VE node | API endpoint + token (or username/password) |
| A cloud-init template on the node | e.g. an Ubuntu cloud image imported as a template (VMID 9000) |
| An SSH public key | injected into the VM via cloud-init |

Export your Proxmox credentials so the tooling can authenticate (matches the bundled
`examples/01-basic-vm/`):

```bash
export PROXMOX_VE_ENDPOINT="https://192.168.2.6:8006"
export PROXMOX_VE_API_TOKEN="user@realm!token-id=secret"
export TF_VAR_ssh_public_key="$(cat ~/.ssh/id_rsa.pub)"
```

## Step 1 — Ask Claude to provision the VM

The skill activates on natural-language infrastructure requests. Be specific about resources and the
source template:

```text
Provision a new Ubuntu VM on Proxmox from my cloud-init template (VMID 9000):
2 vCPUs, 4 GB RAM, a static IP, and my SSH key injected.
```

The skill consults its `reference/cloud-init-patterns.md`, validates the template with
`tools/validate_template.py`, and provisions the VM through `proxmoxer` (or generates IaC — Step 3).

## Step 2 — Verify the VM and cluster

```text
Check the health of my Proxmox cluster and confirm the new VM is running.
```

This runs the bundled health helpers (`tools/cluster_status.py`, `check_cluster_health.py`,
`check_ceph_health.py`) and summarizes node + storage + VM status.

## Step 3 — Generate reproducible IaC (optional)

Prefer Terraform/OpenTofu over an imperative create? Ask for it — the skill follows the patterns in
its reference docs and the worked `examples/01-basic-vm/` (a `main.tf` + `variables.tf` using the
Telmate provider):

```text
Generate Terraform for that VM using the Telmate Proxmox provider, so I can `terraform plan` it.
```

## What you get

A running VM cloned from your template with a static IP and SSH access — provisioned imperatively via
`proxmoxer`, or as `terraform plan`-ready IaC you can commit.

## Notes

- The skill is verified against a single-node setup (`pve1`) over the Proxmox API and SSH.
- It also carries reference docs (networking, storage, QEMU guest agent), multi-node workflows
  (cluster formation, Ceph deployment), and an anti-patterns guide — see the reference page.

## Next steps

- Reference: [`docs/plugins/proxmox-infra.md`](../../plugins/proxmox-infra.md)
- Plugin README: [`plugins/boss-homelab/proxmox-infra/README.md`](../../../plugins/boss-homelab/proxmox-infra/README.md)
- Back to all [tutorials](../README.md)
