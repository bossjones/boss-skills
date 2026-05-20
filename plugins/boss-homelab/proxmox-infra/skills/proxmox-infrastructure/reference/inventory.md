# pve1 Inventory Snapshot

Volatile state for the homelab Proxmox node. Update when hardware, VMs, or LXC containers change. Verify against live state with `${CLAUDE_SKILL_DIR}/tools/cluster_status.py` before relying on values here.

## Node

- **Hostname:** pve1
- **Address:** 192.168.2.6
- **PVE version:** 8.4.16
- **Form factor:** Intel NUC / Mini PC
- **CPU:** 11th Gen Intel Core i7-11700B (8C/16T @ 3.20 GHz)
- **RAM:** 62.4 GB
- **Disks:**
  - 1x 931 GB NVMe (GIGABYTE GP-AG41TB) — boot disk
  - 1x 1.8 TB SSD (P40 Game Drive) — data storage
  - 1x 931 GB HDD (Toshiba MQ04UBF100)
- **NICs:**
  - `enp89s0` (onboard) — bridged on `vmbr0`
  - `enx00e04c680769` (USB) — bridged on `vmbr1`

## Networking

- `vmbr0`: Management — 192.168.2.0/24, bridge port `enp89s0`, no VLAN tagging
- `vmbr1`: Secondary — bridge port `enx00e04c680769`, no VLAN tagging

## Storage

| Pool | Type | Size | Purpose |
|------|------|------|---------|
| `local` | Directory | 93.9 GB | ISOs, templates, backups |
| `local-lvm` | LVM-thin | 794.8 GB | VM/container disks |
| `backups1` | Directory | 915.8 GB | Backups |
| `mydata` | Directory | 1.8 TB | Data |
| `nfs001` | NFS | shared | Backups/ISOs |

## VMs

| VMID | Name | CPUs | Memory |
|------|------|------|--------|
| 104 | ubuntu-2204 | 8 | 30 GB |
| 105 | ubuntu-2404 | 4 | 8 GB |
| 106 | ubuntu-2404b | 4 | 8 GB |
| 107 | so2 | 4 | 24 GB |

## LXC Containers

| VMID | Name | CPUs | Memory |
|------|------|------|--------|
| 100 | prometheus | 2 | 4 GB |
| 101 | openobserve | 1 | 512 MB |
| 102 | grafana | 1 | 1 GB |
| 103 | prometheus-alertmanager | 1 | 256 MB |
