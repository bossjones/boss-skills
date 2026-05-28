<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Any tips and tricks involving facts in ansible that might be helpful in 2026? What about testing practices ? Also during CI what’s the best way to test against ephemeral infra? Docker ? What are my

Options ?

Good, I have comprehensive research. Let me compile this into a solid answer covering all three areas: facts tips \& tricks, testing practices, and CI ephemeral infrastructure options.

Here's a thorough breakdown across all three areas — facts, testing, and CI ephemeral infra.

***

## Ansible Facts: Tips \& Tricks in 2026

### Surgical Fact Gathering with `gather_subset`

Fact gathering adds ~3+ seconds of overhead per host. Rather than the binary `gather_facts: false`, use `gather_subset` to collect exactly what you need:[^1_1]

```yaml
- hosts: all
  gather_facts: true
  gather_subset:
    - '!all'
    - '!min'
    - network
    - distribution
```

Negation prefixes (`!hardware`, `!virtual`) let you exclude expensive subsets like disk/BIOS enumeration while keeping network and OS facts. For plays that genuinely need zero facts (restarts, cache flushes), `gather_facts: false` is still the right call.[^1_2][^1_1]

### Fact Caching Strategies

The default memory cache is ephemeral and dies with the run. For large fleets, use a persistent backend in `ansible.cfg`:[^1_3]

```ini
[defaults]
gathering = smart
fact_caching = community.general.redis
fact_caching_connection = localhost:6379:0
fact_caching_timeout = 86400
```

`gathering = smart` means Ansible skips re-gathering if a valid cache entry exists — the biggest single win for multi-play pipelines. Redis is the best production backend (via `community.general`); `jsonfile` works fine for local dev and homelabs. One important gotcha: **watch out for `gather_subset` interactions with `smart` gathering** — there's an open Ansible bug (ansible/ansible\#84502) where the first play's `gather_subset` poisons the cache for subsequent plays requesting different subsets.[^1_4][^1_5][^1_6][^1_7][^1_8]

### Custom Facts on Managed Nodes

```
Drop JSON or INI files into `/etc/ansible/facts.d/*.fact` on remote nodes — they're auto-loaded into `ansible_local.<filename>.<key>`:[^1_9][^1_10]
```

```json
// /etc/ansible/facts.d/app.fact
{"version": "2.4.1", "tier": "prod", "deploy_key": "abc123"}
```

Access via `{{ ansible_local.app.version }}`. Key rules:[^1_11]

- Files must be **executable** if they're scripts (and output valid JSON to stdout)
- Files must be **non-executable** if they're flat JSON/INI
- Use this over `set_fact` for state that should survive across playbook runs


### `set_fact` vs. `cacheable: true` Anti-patterns

`set_fact` is session-scoped by default. Adding `cacheable: true` writes to the fact cache backend, but there are real gotchas:[^1_12][^1_13]

- It sets **two variables** internally — a hostvar AND an `ansible_facts` entry — which means `meta: clear_facts` doesn't reliably invalidate it[^1_13]
- Prefer `set_stats` for cross-play state passing or actual `/etc/ansible/facts.d/` scripts for durable state[^1_14][^1_15]
- For computed/derived facts, use Jinja2 in `set_fact` inline rather than registering a shell command just to capture output[^1_9]


### Execution Environments for Consistent Fact Modules

Package your Ansible runtime into an OCI Execution Environment so every workstation and CI runner gets the same collection versions (and thus the same fact-gathering modules):[^1_16][^1_17]

```dockerfile
FROM ghcr.io/ansible/community-ansible-dev-tools:latest
RUN pip install ansible-core==2.19 && \
    ansible-galaxy collection install community.general
```

This matters because `community.general.redis` for fact caching, Windows fact `.ps1` scripts, and cloud-specific setup modules all vary by collection version.[^1_18][^1_19]

***

## Testing Practices

### The Testing Pyramid for Ansible

A solid 2026 testing stack looks like:[^1_20][^1_21]


| Layer | Tool | What It Catches |
| :-- | :-- | :-- |
| Lint/syntax | `yamllint` + `ansible-lint` | Style, deprecated modules, FQCN violations |
| Unit (fast) | `ansible-test units` | Module logic in isolation |
| Integration | Molecule + Testinfra/Ansible verifier | Role behavior on real OS images |
| Idempotency | `molecule test` (converge twice) | Re-run safety |
| End-to-end | Full playbook in CI against containers | Cross-role interactions |

### Molecule in 2026

Molecule is now at **v26.3.0** (released March 2026), installable via `ansible-dev-tools`:[^1_22]

```bash
python3 -m pip install -U ansible-dev-tools
# or just molecule
python3 -m pip install "molecule-plugins[docker,podman]" pytest-testinfra
```

The current release emphasizes collection-aware scenario creation and Ansible-native workflows. Note that **ansible-core 2.19.0 briefly broke Molecule** in mid-2025 (NoneType error on `cmd_args`)  — pin your `ansible-core` version in your EE image and test upgrades before rolling out.[^1_23][^1_24]

### Verifier: Ansible vs. Testinfra

The community consensus as of 2025-2026:[^1_25][^1_26]

- **Ansible verifier** (default): simpler, no extra deps, works great for YAML-native teams
- **Testinfra + pytest**: better for teams comfortable with Python; survives individual test failures and shows a full pytest summary (unlike Ansible which bails on first failure)[^1_27][^1_25]

```python
# molecule/default/tests/test_nginx.py
def test_nginx_running(host):
    nginx = host.service("nginx")
    assert nginx.is_running
    assert nginx.is_enabled

def test_port_80(host):
    assert host.socket("tcp://0.0.0.0:80").is_listening
```

Pair Testinfra with `pytest-xdist` for parallel test execution across multiple instances.[^1_25]

### `ansible-test` for Collections

If you're building or maintaining collections (relevant for your MCP/Claude plugin work), `ansible-test` is the right tool — it's purpose-built for collection sanity, units, and integration:[^1_28][^1_26]

```yaml
# .github/workflows/ansible-test.yml
- uses: ansible-community/ansible-test-gh-action@release/v1
  with:
    ansible-core-version: stable-2.19
    testing-type: integration
    test-deps: community.general
```


***

## CI Ephemeral Infrastructure Options

This is where you have the most choices in 2026. Here's the full landscape:

### Option 1: Docker / Podman Containers (Best for Most Cases)

The de facto standard for fast, cheap CI. Molecule's Docker and Podman drivers spin containers up and tear them down per test run.[^1_29][^1_30]

**Podman** is gaining serious traction for enterprise/RHEL environments because it's rootless (no privileged daemon) and available in RHEL repos without a separate install:[^1_31]

```yaml
# molecule/default/molecule.yml
driver:
  name: podman
platforms:
  - name: instance
    image: "docker.io/geerlingguy/docker-ubuntu2404-ansible:latest"
    pre_build_image: true
    privileged: true
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup:rw
    cgroupns_mode: host
```

**Key limitation**: containers can't test things that require real kernel behaviors — systemd (partially works with privileged containers), iptables, kernel modules, or actual network interface manipulation. For those, you need VMs.

### Option 2: Vagrant + VirtualBox/libvirt (Best for VM-level Testing)

When you need a real OS with a real kernel. Works great locally and on self-hosted runners:[^1_32][^1_21]

```ruby
# Vagrantfile
Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-22.04"
  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "site.yml"
  end
end
```

GitHub Actions hosted runners don't support VirtualBox nested virt — so this is a **self-hosted runner** or local-only strategy.[^1_32]

### Option 3: Kind / Minikube (K8s-Targeted Testing)

For testing Ansible roles that deploy to Kubernetes, `kind` (Kubernetes-in-Docker) is the cleanest option:[^1_33][^1_34][^1_35]

```yaml
# molecule/k8s/molecule.yml
driver:
  name: delegated
platforms:
  - name: kind-cluster
```

Pair with a `prepare.yml` that runs `kind create cluster`. Works well in GitHub Actions since it's just Docker under the hood. Given you're running K3s in your homelab, this mirrors that workflow reasonably well.[^1_33]

### Option 4: Ephemeral Cloud VMs (AWS/GCP/Azure)

For full fidelity at the cost of ~2-5 min spin-up time and cloud spend. Use Ansible itself to provision then destroy:[^1_36][^1_37]

```yaml
# CI create step
- name: Provision ephemeral EC2
  amazon.aws.ec2_instance:
    name: "ci-test-{{ lookup('env','GITHUB_RUN_ID') }}"
    instance_type: t3.micro
    image_id: ami-0c55b159cbfafe1f0
    state: present
  register: test_instance

# ... run playbooks ...

- name: Terminate
  amazon.aws.ec2_instance:
    instance_ids: "{{ test_instance.instance_ids }}"
    state: absent
```

Tag instances with the CI run ID so they're always cleaned up. This is the gold standard for testing things like real NIC bonding, kernel tuning, or cloud-specific integrations.

### Option 5: Execution Environment + Delegated Driver

The most underrated option for pure CI: run everything inside an Ansible EE container, use the `delegated` Molecule driver, and point at a pre-existing static host (your homelab K3s cluster, a dedicated test VM, etc.). Zero spin-up time, full OS fidelity. Works if you're okay with a shared/persistent test host that gets wiped between runs via a `cleanup.yml`.[^1_38][^1_17]

### Summary Decision Tree

```
Need K8s?           → Kind + delegated driver
Need real kernel?   → Vagrant (self-hosted) or cloud VM
Need fast/cheap CI? → Docker/Podman + Molecule
Building collection?→ ansible-test-gh-action
Full fidelity prod? → Ephemeral cloud VMs
```

Given your Proxmox + K3s homelab setup, a strong pattern is: Docker/Podman for day-to-day role testing in CI, Vagrant or ephemeral Proxmox VMs via the Molecule `delegated` driver for kernel-level testing on self-hosted runners, and Kind for your K8s-targeting playbooks.[^1_31][^1_38][^1_33]
<span style="display:none">[^1_39][^1_40][^1_41][^1_42][^1_43][^1_44][^1_45][^1_46][^1_47][^1_48][^1_49][^1_50][^1_51][^1_52][^1_53][^1_54][^1_55][^1_56][^1_57][^1_58][^1_59][^1_60][^1_61][^1_62][^1_63][^1_64][^1_65][^1_66][^1_67][^1_68][^1_69][^1_70][^1_71][^1_72][^1_73][^1_74]</span>

<div align="center">⁂</div>

[^1_1]: https://www.linkedin.com/pulse/gathering-limitedselectiverestricted-facts-ansible-nilesh-r-joshi

[^1_2]: https://oneuptime.com/blog/post/2026-02-21-how-to-minimize-ansible-fact-gathering-for-performance/view

[^1_3]: https://docs.ansible.com/projects/ansible/latest/plugins/cache.html

[^1_4]: https://docs.openstack.org/kolla-ansible/2025.1/user/ansible-tuning.html

[^1_5]: https://docs.openstack.org/kolla-ansible/2023.1/user/ansible-tuning.html

[^1_6]: https://www.redhat.com/ja/blog/ansible-fact-cache-redis

[^1_7]: https://docs.ansible.com/ansible/latest/collections/community/general/redis_cache.html

[^1_8]: https://github.com/ansible/ansible/issues/84502

[^1_9]: https://www.linkedin.com/pulse/how-create-use-custom-fact-variables-ansible-charanjit-singh-cheema--daskf

[^1_10]: https://www.ansiblebyexample.com/articles/what-are-ansible-facts

[^1_11]: https://www.reddit.com/r/ansible/comments/iipgs7/understanding_custom_facts/

[^1_12]: https://www.reddit.com/r/ansible/comments/o4zys7/need_clarification_on_set_fact_module/

[^1_13]: https://github.com/ansible/ansible/issues/50556

[^1_14]: https://groups.google.com/g/ansible-project/c/JaTbN0h4Moo

[^1_15]: https://forum.ansible.com/t/set-fact-and-fact-caching/17386

[^1_16]: https://medium.com/@maftun.hashimli/from-code-to-converged-state-high-performance-ansible-strategies-59bda74d1579

[^1_17]: https://docs.ansible.com/projects/ansible/latest/getting_started_ee/index.html

[^1_18]: https://forum.ansible.com/t/windows-custom-facts-help/33835

[^1_19]: https://forum.ansible.com/c/news/releases/18/l/top?page=3\&per_page=50

[^1_20]: https://github.com/universalvishwa/ansible-molecule-testing

[^1_21]: https://www.augmentedmind.de/2022/12/11/infrastructure-testing-ansible/

[^1_22]: https://forum.ansible.com/t/release-announcement-molecule-v26-3-0/45490

[^1_23]: https://forum.ansible.com/t/help-test-molecule-v25-9-0-rc1-pre-release/44345

[^1_24]: https://github.com/ansible/ansible/issues/85515

[^1_25]: https://forum.ansible.com/t/molecule-end-to-end-testing-via-ansible-verifier/5583

[^1_26]: https://www.reddit.com/r/ansible/comments/1l0pv42/molecule_vs_ansibletest_vs_ansibletox/

[^1_27]: https://oneuptime.com/blog/post/2026-02-21-how-to-write-molecule-verify-tests-with-testinfra/view

[^1_28]: https://github.com/marketplace/actions/ansible-test

[^1_29]: https://medium.com/contino-engineering/testing-ansible-automation-with-molecule-pt-1-66ab3ea7a58a

[^1_30]: https://oneuptime.com/blog/post/2026-02-21-how-to-install-molecule-for-ansible-testing/view

[^1_31]: https://oneuptime.com/blog/post/2026-02-21-how-to-configure-molecule-with-podman-driver/view

[^1_32]: https://github.com/borjatur/kubernetes-using-ansible-vagrant

[^1_33]: https://github.com/geerlingguy/ansible-for-kubernetes/issues/36

[^1_34]: https://sdk.operatorframework.io/docs/building-operators/ansible/testing-guide/

[^1_35]: https://stackoverflow.com/questions/75319946/how-can-i-test-ansible-roles-used-to-install-applications-in-kubernetes

[^1_36]: https://developers.redhat.com/articles/2023/07/12/how-create-instance-gcp-using-ansible-cli

[^1_37]: https://medium.com/elevate-tech/automatic-cloud-vm-configuration-with-ansible-and-gitlab-9cfdbf6f8a83

[^1_38]: https://www.sysbee.net/blog/testing-ansible-playbooks-with-molecule/

[^1_39]: https://docs.ansible.com/projects/ansible/latest/tips_tricks/index.html

[^1_40]: https://www.youtube.com/watch?v=Ely_8MLdaPE

[^1_41]: https://www.youtube.com/watch?v=S6sx59-ShYU

[^1_42]: https://forum.ansible.com/t/improving-ansible-facts-documentation/40075

[^1_43]: https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_vars_facts.html

[^1_44]: https://www.automatesql.com/blog/what-are-ansible-facts-using-system-data-to-make-your-automation-smarter

[^1_45]: https://stackoverflow.com/questions/78959098/ansible-custom-facts-for-a-remote-node-not-the-control-node-how-is-that-set-u

[^1_46]: https://medium.com/@kartikdudeja21/devops-sandbox-build-your-own-kubernetes-lab-with-vagrant-ansible-11d0efe2a145

[^1_47]: https://forum.ansible.com/t/cfgmgmtcamp-2026-discussion-8-12-instant-ansible-test-target-updates-without-announcements/45295

[^1_48]: https://blog.octo.com/how-does-it-work-kubernetes-episode-4-how-to-ansible-your-coreos-and-etcd

[^1_49]: https://github.com/geerlingguy/ansible-for-devops-manuscript/blob/master/chapter13.txt

[^1_50]: https://forum.ansible.com/t/goodbye-2025-and-cheers-to-2026/45012

[^1_51]: https://stackoverflow.com/questions/32703874/fastest-way-to-gather-facts-to-fact-cache

[^1_52]: https://docs.ansible.com/ansible/latest/dev_guide/testing.html

[^1_53]: https://dev.to/admantium/ansible-boost-task-execution-speed-54b3

[^1_54]: https://pypi.org/project/molecule-podman/

[^1_55]: https://github.com/ansible-community/ansible-test-gh-action

[^1_56]: https://stackoverflow.com/questions/47461359/ansible-fact-caching-in-redis

[^1_57]: https://ansible.readthedocs.io/projects/molecule/examples/podman/

[^1_58]: https://docs.nautobot.com/projects/ansible/en/latest/getting_started/contributing/testing_with_gha/

[^1_59]: https://ansible.readthedocs.io/projects/molecule/installation/

[^1_60]: http://github.com/ansible/ansible-core-test-container/actions

[^1_61]: https://dev.to/koh_sh/redis-can-make-ansible-only-a-bit-faster-39g7

[^1_62]: https://www.reddit.com/r/ansible/comments/196s899/how_can_i_test_ansible_by_using_github_actions/

[^1_63]: https://forum.ansible.com/t/gather-minimal-facts-within-playbook/28182

[^1_64]: https://stackoverflow.com/questions/58997978/how-to-debug-your-tests-when-using-testinfra-as-verifier-in-molecule

[^1_65]: https://docs.ansible.com/projects/ansible/latest/collections/google/cloud/gcp_compute_instance_template_module.html

[^1_66]: https://stackoverflow.com/questions/71692791/is-it-possible-to-gather-only-specific-facts-in-ansible

[^1_67]: https://www.linkedin.com/posts/swagata-banerjee-4808a0200_30daysofdevops-ansible-aws-activity-7326114892208332800-OqkJ

[^1_68]: https://opensource.com/article/19/5/using-testinfra-ansible-verify-server-state

[^1_69]: https://docs.ansible.com/projects/ansible/latest/collections/google/cloud/gcp_compute_instance_module.html

[^1_70]: https://docs.oracle.com/en/learn/oci-fam-patching-ansible/index.html

[^1_71]: https://github.com/oracle/oci-ansible-collection/blob/master/docs/guides/awx/awx-post-deployment-steps.md

[^1_72]: https://stackoverflow.com/questions/74855818/ansible-fact-setting-using-set-fact-not-persisting-across-runs

[^1_73]: https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.4/html-single/creating_and_consuming_execution_environments/index

[^1_74]: https://github.com/ansible/molecule/issues/2043


---

# vagrant isn't used anymore on macos, how could I test with molecule and something like vmware or tart or utm ?

You're right — Vagrant is essentially dead on macOS ARM, and the situation is fragmented. Here are the real options that actually work on Apple Silicon in 2026:

***

## VM-Based Molecule Testing on macOS (Apple Silicon)

### Option 1: Tart + `vagrant-tart` (Best macOS-native option)

**Tart** by Cirrus Labs is purpose-built for Apple Silicon, using Apple's native `Virtualization.Framework` directly. It's what Cirrus CI uses for their own GitHub Actions runners and it's genuinely fast. There's a `vagrant-tart` Vagrant provider that plugs into Molecule's existing `vagrant` driver so you don't need a new Molecule driver at all:[^2_1][^2_2][^2_3]

```bash
brew install cirruslabs/cli/tart
gem install vagrant
vagrant plugin install vagrant-tart
pip install molecule-vagrant
```

Then your `molecule.yml` uses the existing vagrant driver with `provider.name: tart`:[^2_1]

```yaml
driver:
  name: vagrant
  provider:
    name: tart
platforms:
  - name: instance
    cpus: 4
    memory: 4096
    instance_raw_config_args:
      - "ssh.username = 'admin'"
      - "ssh.password = 'admin'"
    provider_options:
      image: ghcr.io/cirruslabs/ubuntu:latest
      name: molecule-test
```

Tart OCI images are stored in container registries, so you pull them like Docker images (`ghcr.io/cirruslabs/ubuntu:latest`, `ghcr.io/cirruslabs/fedora:latest`, etc.). The big win: near-native performance since it's not emulating anything.[^2_4]

***

### Option 2: Lima + `molecule-lima` (Most flexible)

**Lima** (`lima`) is the lower-level engine behind Colima and Rancher Desktop. A dedicated `molecule-lima` driver (v0.0.3, released November 2025) was specifically built for Apple Silicon Ansible testing:[^2_5][^2_6]

```bash
brew install lima
pip install molecule-lima
```

Lima supports multiple VM types (QEMU, Apple VZ), multiple distros, and can run x86_64 VMs under Rosetta 2 on Apple Silicon — handy when you need to validate against amd64 targets. It's the most flexible option if you need to mix architectures.[^2_7]

***

### Option 3: `molecule-qemu` (Lightweight, no extra VM manager)

**`molecule-qemu`** talks to QEMU directly — no Vagrant, no Lima, just `brew install qemu`:[^2_8][^2_9]

```bash
brew install qemu cdrtools
pip install molecule-qemu
```

```yaml
driver:
  name: molecule-qemu
platforms:
  - name: ubuntu-arm
    image: https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-arm64.img
    image_arch: aarch64
    ssh_port: 10022
    ssh_user: ubuntu
```

**Caveat**: the project [explicitly states](https://github.com/andreygubarev/molecule-qemu) it supports Molecule `0.5.x` and does **not** plan to support `0.6.x+`. If you're on modern Molecule (26.x), this may require maintaining a pinned older Molecule in a separate venv.[^2_9]

***

### Option 4: Multipass + `molecule-multipass`

**Multipass** is Canonical's lightweight Ubuntu VM launcher for macOS, uses native Apple VZ under the hood:[^2_10]

```bash
brew install --cask multipass
pip install molecule-multipass
```

```yaml
driver:
  name: molecule_multipass
platforms:
  - name: instance
```

It's dead simple but **Ubuntu-only** — no RHEL/Rocky/Fedora images. Great if your targets are Ubuntu-based (which based on your K3s/Proxmox setup they likely are).

***

### Option 5: VMware Fusion + `molecule-vmware` (vSphere-targeted)

`molecule-vmware` is designed for vSphere environments, not local Fusion. If you want Fusion locally, the path is the Molecule `delegated` driver + a custom `create.yml` that calls `vmrun` or the `community.vmware` collection to clone a template. More manual setup but gives you full VMware fidelity — useful if your actual prod targets are VMware VMs.[^2_11][^2_12]

***

### Quick Comparison

| Option | Molecule Driver | Distros | Arch | Complexity |
| :-- | :-- | :-- | :-- | :-- |
| **Tart** | `vagrant` (tart provider) | Ubuntu, Fedora, Debian, macOS | arm64 native | Low |
| **Lima** | `molecule-lima` | Any cloud image | arm64 + x86 via Rosetta | Medium |
| **QEMU direct** | `molecule-qemu` | Ubuntu, Debian | arm64 + x86 | Medium (old Molecule only) |
| **Multipass** | `molecule-multipass` | Ubuntu only | arm64 native | Very low |
| **VMware Fusion** | `delegated` + custom create | Any | arm64 | High |

For your use case (fast local dev loop on an Apple Silicon Mac, multi-distro, feeds into GitHub Actions CI with Docker), **Tart is the cleanest path**  — native speed, OCI-style image management, and `vagrant-tart` means zero changes to your existing Molecule vagrant driver config. Lima is the runner-up if you need Rosetta x86_64 testing or non-Tart image registries.[^2_3][^2_6][^2_7][^2_1]
<span style="display:none">[^2_13][^2_14][^2_15][^2_16][^2_17][^2_18][^2_19][^2_20][^2_21][^2_22][^2_23][^2_24][^2_25][^2_26][^2_27][^2_28][^2_29][^2_30][^2_31][^2_32][^2_33][^2_34][^2_35][^2_36]</span>

<div align="center">⁂</div>

[^2_1]: https://letiemble.github.io/vagrant-tart/molecule.html

[^2_2]: https://github.com/cirruslabs/tart

[^2_3]: https://tart.run

[^2_4]: https://www.scaleway.com/en/docs/tutorials/run-manage-linux-vm-on-apple-silicon-tart/

[^2_5]: https://www.piwheels.org/project/molecule-lima/

[^2_6]: https://github.com/filatof/molecule-lima

[^2_7]: https://100things.wzzrd.com/2024/04/04/Developing-Ansible-Automation-Content-on-Apple-Silicon.html

[^2_8]: https://pypi.org/project/molecule-qemu/0.4.0/

[^2_9]: https://github.com/andreygubarev/molecule-qemu

[^2_10]: https://pypi.org/project/molecule-multipass/

[^2_11]: https://github.com/ansible-community/molecule-vmware

[^2_12]: https://oneuptime.com/blog/post/2026-02-21-molecule-delegated-driver/view

[^2_13]: https://www.youtube.com/watch?v=3FUAKV4VRyI

[^2_14]: https://discussions.apple.com/thread/255923493

[^2_15]: https://megaw.co.za/molecule/

[^2_16]: https://www.tauceti.blog/posts/testing-ansible-roles-with-molecule-libvirt-vagrant-qemu-kvm/

[^2_17]: https://community.broadcom.com/vmware-cloud-foundation/discussion/creating-a-new-vm-on-a-2025-macbook-air-m4

[^2_18]: https://github.com/jonashackt/molecule-ansible-vagrant-macosx

[^2_19]: https://forum.ansible.com/t/molecule-with-docker-on-mac-m2-causes-com-apple-virtualization-virtualmachine-crashed-when-gather-facts-is-enabled/2902

[^2_20]: https://gineesh.com/molecule/

[^2_21]: https://redhatnordicssa.github.io/test-ansible-role-molecule-podman

[^2_22]: https://opensource.com/article/18/12/testing-ansible-roles-molecule

[^2_23]: https://www.reddit.com/r/ansible/comments/1auz7tr/what_test_vms_can_i_use_on_m1_mac/

[^2_24]: https://www.reddit.com/r/ansible/comments/1czhczz/using_molecule_docker_driver_on_macos/

[^2_25]: https://github.com/ansible-community/molecule-docker/issues/149

[^2_26]: https://stackoverflow.com/questions/54765006/how-to-use-molecule-inside-a-vm-to-test-an-ansible-role-that-installs-docker

[^2_27]: https://github.com/ansible/molecule/issues/1479

[^2_28]: https://formulae.brew.sh/formula/molecule

[^2_29]: https://www.linkedin.com/posts/robpotvin_github-cirruslabstart-macos-and-linux-activity-7048975638082277377-WAVm

[^2_30]: https://habr.com/en/articles/966276/

[^2_31]: https://stackoverflow.com/questions/72998172/test-ansible-roles-with-molecule-and-vagrant

[^2_32]: https://www.youtube.com/watch?v=qgu9g5ri1ow

[^2_33]: https://forum.ansible.com/t/how-to-manage-vagrant-vm-lifecycle-with-ansible/44743

[^2_34]: https://pypi.org/project/molecule-vagrant/

[^2_35]: https://oneuptime.com/blog/post/2026-02-21-how-to-configure-molecule-with-vagrant-driver/view

[^2_36]: https://habr.com/ru/articles/966276/

