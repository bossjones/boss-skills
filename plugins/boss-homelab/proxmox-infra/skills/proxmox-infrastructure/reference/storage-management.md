# Proxmox Storage Management

## Overview

Proxmox VE supports multiple storage backends. This guide focuses on the storage architecture of the pve1 standalone server: LVM-thin for VM disks and directory/NFS storage for backups and ISOs.

## pve1 Server Storage Architecture

### Hardware Configuration

**Node pve1:**

```text
/dev/nvme0n1  - 931GB GIGABYTE GP-AG41TB  → Boot disk + LVM
/dev/sda      - 1.8TB P40 Game Drive SSD  → Data storage (mydata, backups1)
/dev/sdb      - 29GB Cruzer Glide USB     → (removable)
/dev/sdd      - 931GB Toshiba HDD         → Additional storage
```

### Storage Pools

```text
Storage Pool     Type       Backend    Purpose
-------------    ----       -------    -------
local            dir        Directory  ISO images, templates, backups (93.9 GB)
local-lvm        lvmthin    LVM-thin   VM/container disks (794.8 GB)
backups1         dir        Directory  Backups, ISOs, templates (915.8 GB)
mydata           dir        Directory  Data, ISOs, backups (1.8 TB)
nfs001           nfs        NFS Share  Backups, ISOs (shared)
```

## LVM Storage

### LVM-thin Configuration

**Advantages:**

- Thin provisioning (overcommit storage)
- Fast snapshots
- Local to each node (low latency)
- No network overhead

**Disadvantages:**

- No HA (tied to single node)
- No live migration with storage
- Limited to node's local disk size

**Check LVM usage:**

```bash
# View volume groups
vgs

# View logical volumes
lvs

# View thin pool usage
lvs -a | grep thin
```

**Example output:**

```text
  LV            VG  Attr       LSize   Pool Origin Data%
  data          pve twi-aotz-- 850.00g             45.23
  vm-101-disk-0 pve Vwi-aotz--  50.00g data        12.45
```

### Managing LVM Storage

**Extend thin pool (if boot disk has space):**

```bash
# Check free space in VG
vgs pve

# Extend thin pool
lvextend -L +100G pve/data
```

**Create VM disk manually:**

```bash
# Create 50GB disk for VM 101
lvcreate -V 50G -T pve/data -n vm-101-disk-0
```

## Storage Configuration in Proxmox

### Add Storage via Web UI

**Datacenter → Storage → Add:**

1. **Directory** - For ISOs and backups
2. **LVM-Thin** - For local VM disks
3. **RBD** - For CEPH VM disks
4. **CephFS** - For shared files

### Add Storage via CLI

**NFS:**

```bash
pvesm add nfs nfs001 \
  --server 192.168.2.10 \
  --export /mnt/tank/proxmox \
  --content images,backup,iso,vztmpl,snippets,rootdir
```

**Directory:**

```bash
pvesm add dir mydata \
  --path /mnt/mydata \
  --content images,backup,iso,vztmpl,snippets,rootdir
```

## VM Disk Management

### Create VM Disk on LVM-thin

**Via CLI:**

```bash
# Create 100GB disk for VM 108 on local-lvm
qm set 108 --scsi1 local-lvm:100
```

**Via API (Python):**

```python
from proxmoxer import ProxmoxAPI

proxmox = ProxmoxAPI('192.168.2.6', user='root@pam', password='pass')
proxmox.nodes('pve1').qemu(108).config.put(scsi1='local-lvm:100')
```

### Move VM Disk Between Storage

**Move from local-lvm to mydata:**

```bash
qm move-disk 108 scsi0 mydata --delete 1
```

### Resize VM Disk

**Grow disk (can't shrink):**

```bash
# Grow VM 104's scsi0 by 50GB
qm resize 104 scsi0 +50G
```

**Inside VM (expand filesystem):**

```bash
# For ext4
sudo resize2fs /dev/sda1

# For XFS
sudo xfs_growfs /
```

## Backup and Restore

### Backup to Storage

**Create backup:**

```bash
# Backup VM 104 to local storage
vzdump 104 --storage local --mode snapshot --compress zstd

# Backup to backups1
vzdump 104 --storage backups1 --mode snapshot --compress zstd
```

**Scheduled backups (via Web UI):**

Datacenter → Backup → Add:

- Schedule: Daily at 2 AM
- Storage: backups1
- Mode: Snapshot
- Compression: ZSTD
- Retention: Keep last 7

### Restore from Backup

**List backups:**

```bash
ls /var/lib/vz/dump/
```

**Restore:**

```bash
# Restore to same VMID
qmrestore /var/lib/vz/dump/vzdump-qemu-104-2024_01_15-02_00_00.vma.zst 104

# Restore to new VMID on local-lvm
qmrestore /var/lib/vz/dump/vzdump-qemu-104-2024_01_15-02_00_00.vma.zst 108 --storage local-lvm
```

## Performance Tuning

### LVM Performance

**Use SSD discard:**

```bash
# Enable discard on VM disk
qm set 104 --scsi0 local-lvm:vm-104-disk-0,discard=on,ssd=1
```

## Troubleshooting

### LVM Out of Space

**Check thin pool usage:**

```bash
lvs pve/data -o lv_name,data_percent,metadata_percent
```

**If thin pool > 90% full:**

```bash
# Extend if VG has space
lvextend -L +100G pve/data

# OR delete unused VM disks
lvremove pve/vm-XXX-disk-0
```

### Storage Performance Issues

**Test disk I/O:**

```bash
# Test sequential write
dd if=/dev/zero of=/tmp/test bs=1M count=1024 oflag=direct
```

## Best Practices

1. **Use LVM-thin for VM disks** - Thin provisioning with fast snapshots on local NVMe
2. **Separate backup storage** - Use backups1 or NFS for backups, keep local for ISOs/templates
3. **Regular backups** - Automated daily backups to backups1 or NFS
4. **Monitor thin pool usage** - Alert when LVM thin pool exceeds 80%
5. **Use SSD discard** - Enable discard on LVM-thin backed VMs for NVMe
6. **Plan for growth** - Leave 20% free space in LVM thin pool

## Further Reading

- [Proxmox VE Storage Documentation](https://pve.proxmox.com/wiki/Storage)
