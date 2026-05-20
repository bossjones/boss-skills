# Proxmox API Reference

## Overview

The Proxmox API enables programmatic management of the cluster via REST. This reference focuses on common patterns for Python (proxmoxer) and Terraform/Ansible usage.

## Authentication Methods

### API Tokens (Recommended)

**Create API token via CLI:**

```bash
pveum user token add <user>@<realm> <token-id> --privsep 0
```

**Environment variables:**

```bash
export PROXMOX_VE_API_TOKEN="user@realm!token-id=secret"
export PROXMOX_VE_ENDPOINT="https://192.168.2.6:8006"
```

### Password Authentication

```bash
export PROXMOX_VE_USERNAME="root@pam"
export PROXMOX_VE_PASSWORD="password"
export PROXMOX_VE_ENDPOINT="https://192.168.2.6:8006"
```

## Python API Usage (proxmoxer)

### Installation

```bash
# Using uv inline script metadata
# /// script
# dependencies = ["proxmoxer", "requests"]
# ///
```

### Basic Connection

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["proxmoxer", "requests"]
# ///

from proxmoxer import ProxmoxAPI
import os

# Connect using API token
proxmox = ProxmoxAPI(
    os.getenv("PROXMOX_VE_ENDPOINT").replace("https://", "").replace(":8006", ""),
    user=os.getenv("PROXMOX_VE_USERNAME"),
    token_name=os.getenv("PROXMOX_VE_TOKEN_NAME"),
    token_value=os.getenv("PROXMOX_VE_TOKEN_VALUE"),
    verify_ssl=False
)

# OR using password
proxmox = ProxmoxAPI(
    '192.168.2.6',
    user='root@pam',
    password=os.getenv("PROXMOX_VE_PASSWORD"),
    verify_ssl=False
)
```

### Common Operations

**List VMs:**

```python
# Get all VMs across cluster
for node in proxmox.nodes.get():
    node_name = node['node']
    for vm in proxmox.nodes(node_name).qemu.get():
        print(f"VM {vm['vmid']}: {vm['name']} on {node_name} - {vm['status']}")
```

**Get VM Configuration:**

```python
vmid = 104
node = "pve1"

vm_config = proxmox.nodes(node).qemu(vmid).config.get()
print(f"VM {vmid} config: {vm_config}")
```

**Clone Template:**

```python
template_id = 9000
new_vmid = 108
node = "pve1"

# Clone template
proxmox.nodes(node).qemu(template_id).clone.post(
    newid=new_vmid,
    name="web-01",
    full=1,  # Full clone (not linked)
    storage="local-lvm"
)

# Wait for clone to complete
import time
while True:
    tasks = proxmox.nodes(node).tasks.get()
    clone_task = next((t for t in tasks if t['type'] == 'qmclone' and str(t['id']) == str(new_vmid)), None)
    if not clone_task or clone_task['status'] == 'stopped':
        break
    time.sleep(2)
```

**Update VM Configuration:**

```python
# Set cloud-init parameters
proxmox.nodes(node).qemu(vmid).config.put(
    ipconfig0="ip=192.168.2.100/24,gw=192.168.2.1",
    nameserver="192.168.2.1",
    searchdomain="local",
    sshkeys="ssh-rsa AAAA..."
)
```

**Start/Stop VM:**

```python
# Start VM
proxmox.nodes(node).qemu(vmid).status.start.post()

# Stop VM (graceful)
proxmox.nodes(node).qemu(vmid).status.shutdown.post()

# Force stop
proxmox.nodes(node).qemu(vmid).status.stop.post()
```

**Delete VM:**

```python
proxmox.nodes(node).qemu(vmid).delete()
```

### Cluster Operations

**Get Cluster Status:**

```python
cluster_status = proxmox.cluster.status.get()
for node in cluster_status:
    if node['type'] == 'node':
        print(f"Node: {node['name']} - {node['online']}")
```

**Get Node Resources:**

```python
node_status = proxmox.nodes(node).status.get()
print(f"CPU: {node_status['cpu']*100:.1f}%")
print(f"Memory: {node_status['memory']['used']/1024**3:.1f}GB / {node_status['memory']['total']/1024**3:.1f}GB")
```

### Storage Operations

**List Storage:**

```python
for storage in proxmox.storage.get():
    print(f"Storage: {storage['storage']} - Type: {storage['type']} - {storage['active']}")
```

**Get Storage Content:**

```python
storage = "local-lvm"
content = proxmox.storage(storage).content.get()
for item in content:
    print(f"{item['volid']} - {item.get('vmid', 'N/A')} - {item['size']/1024**3:.1f}GB")
```

## Terraform Provider Patterns

### Basic Resource (VM from Clone)

```hcl
resource "proxmox_vm_qemu" "docker_host" {
  name        = "web-01"
  target_node = "pve1"
  vmid        = 108

  clone       = "ubuntu-template"
  full_clone  = true

  cores   = 4
  memory  = 8192
  sockets = 1

  network {
    bridge = "vmbr0"
    model  = "virtio"
  }

  disk {
    storage = "local-lvm"
    type    = "scsi"
    size    = "50G"
  }

  ipconfig0 = "ip=192.168.2.100/24,gw=192.168.2.1"

  sshkeys = file("~/.ssh/id_rsa.pub")
}
```

### Data Sources

```hcl
# Get template information
data "proxmox_vm_qemu" "template" {
  name        = "ubuntu-template"
  target_node = "pve1"
}

# Get storage information
data "proxmox_storage" "local_lvm" {
  node    = "pve1"
  storage = "local-lvm"
}
```

## Ansible Module Patterns

### Create VM from Template

```yaml
- name: Clone template to create VM
  community.proxmox.proxmox_kvm:
    api_host: "{{ proxmox_api_host }}"
    api_user: "{{ proxmox_api_user }}"
    api_token_id: "{{ proxmox_token_id }}"
    api_token_secret: "{{ proxmox_token_secret }}"
    node: pve1
    vmid: 108
    name: web-01
    clone: ubuntu-template
    full: true
    storage: local-lvm
    net:
      net0: 'virtio,bridge=vmbr0'
    ipconfig:
      ipconfig0: 'ip=192.168.2.100/24,gw=192.168.2.1'
    cores: 4
    memory: 8192
    agent: 1
    state: present
```

### Start VM

```yaml
- name: Start VM
  community.proxmox.proxmox_kvm:
    api_host: "{{ proxmox_api_host }}"
    api_user: "{{ proxmox_api_user }}"
    api_token_id: "{{ proxmox_token_id }}"
    api_token_secret: "{{ proxmox_token_secret }}"
    node: pve1
    vmid: 108
    state: started
```

## pve1 Server Specifics

### Node IP Address

```python
PVE1_NODE = {
    "pve1": "192.168.2.6"
}
```

### Storage Pools

```python
STORAGE_POOLS = {
    "local": "dir",           # Local directory (ISOs, templates, backups)
    "local-lvm": "lvmthin",   # LVM thin on boot disk (VM/container disks)
    "backups1": "dir",        # Backup directory (915 GB)
    "mydata": "dir",          # Data directory (1.8 TB)
    "nfs001": "nfs",          # NFS share (backups, ISOs)
}
```

### Network Bridges

```python
BRIDGES = {
    "vmbr0": "192.168.2.0/24",   # Management (bridge port: enp89s0)
    "vmbr1": None,                # Secondary bridge (bridge port: enx00e04c680769)
}
```

## Error Handling

### Python Example

```python
from proxmoxer import ProxmoxAPI, ResourceException
import sys

try:
    proxmox = ProxmoxAPI('192.168.2.6', user='root@pam', password='pass', verify_ssl=False)
    vm_config = proxmox.nodes('pve1').qemu(104).config.get()
except ResourceException as e:
    print(f"API Error: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}", file=sys.stderr)
    sys.exit(1)
```

### Ansible Example

```yaml
- name: Clone VM with error handling
  community.proxmox.proxmox_kvm:
    api_host: "{{ proxmox_api_host }}"
    # ... config ...
  register: clone_result
  failed_when: false

- name: Check clone result
  ansible.builtin.fail:
    msg: "Failed to clone VM: {{ clone_result.msg }}"
  when: clone_result.failed
```

## API Endpoints Reference

### Common Endpoints

```text
GET    /api2/json/nodes                        # List nodes
GET    /api2/json/nodes/{node}/qemu            # List VMs on node
GET    /api2/json/nodes/{node}/qemu/{vmid}    # Get VM status
POST   /api2/json/nodes/{node}/qemu/{vmid}/clone  # Clone VM
PUT    /api2/json/nodes/{node}/qemu/{vmid}/config # Update config
POST   /api2/json/nodes/{node}/qemu/{vmid}/status/start   # Start VM
POST   /api2/json/nodes/{node}/qemu/{vmid}/status/shutdown # Stop VM
DELETE /api2/json/nodes/{node}/qemu/{vmid}    # Delete VM

GET    /api2/json/cluster/status               # Cluster status
GET    /api2/json/storage                      # List storage
```

## Best Practices

1. **Use API tokens** - More secure than password authentication
2. **Handle SSL properly** - Use `verify_ssl=True` with proper CA cert in production
3. **Check task completion** - Clone/migrate operations are async, poll for completion
4. **Error handling** - Always catch ResourceException and provide meaningful errors
5. **Rate limiting** - Don't hammer the API, add delays in loops
6. **Idempotency** - Check if resource exists before creating
7. **Use VMID ranges** - Reserve ranges for different purposes (templates: 9000-9999, VMs: 100-999)

## Further Reading

- [Proxmox VE API Documentation](https://pve.proxmox.com/pve-docs/api-viewer/)
- [proxmoxer GitHub](https://github.com/proxmoxer/proxmoxer)
- [community.proxmox Collection](https://docs.ansible.com/ansible/latest/collections/community/proxmox/)
