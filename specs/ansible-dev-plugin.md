# Plan: ansible-dev plugin

## Context

This change adds a new Claude Code plugin, **`ansible-dev`**, to the `boss-skills`
marketplace. The user develops Ansible automation for a heterogeneous homelab
(physical Linux, macOS, Proxmox VMs/LXC, and Docker-on-VM) from an Apple Silicon
Mac. Today there is no plugin that teaches the agent harness how to *author* and —
critically — *test* Ansible content with a tight feedback loop before changes ever
touch real hosts. The existing `proxmox-infra` plugin owns Terraform/OpenTofu +
Proxmox provisioning; `ansible-dev` is deliberately **Ansible-only** so the two
don't overlap.

The design is a **hybrid** of two complementary modes, combining this repo's
harness-driven philosophy with the orchestrated multi-agent pipeline pioneered by
[`basher83/lunar-claude`'s `ansible-workflows`
plugin](https://github.com/basher83/lunar-claude/tree/main/plugins/infrastructure/ansible-workflows):

- **Autonomous mode (our core):** PEP 723 helper tools emit **structured JSON** so
  the harness can lint, syntax-check, prove idempotency, run Molecule, and run a
  full layered test loop — parsing results and self-correcting without a human in
  the loop. The keystone is `test_loop.py`.
- **Guided pipeline mode (from lunar-claude):** model-tiered **subagents** and
  **slash commands** drive a stateful pipeline (scaffold → generate → validate →
  review, looping through a debugger on failure) tracked via a `.local.md` state
  file and `.bundle.md` context handoffs.

The testing strategy is layered as a **Docker → Multipass → real-host**
progression: fast container/`delegated` loops for the inner loop, an **ephemeral
Multipass Ubuntu VM** as the full-OS-fidelity "real live machine" rung to validate
provisioning before it touches the homelab, then real homelab hosts last. The
Multipass rung is driven **Ansible-natively** via the
[`theko2fi.multipass`](https://github.com/theko2fi/ansible-multipass-collection)
collection (see [Manage your Multipass VMs with
Ansible](https://theko2fi.medium.com/manage-your-multipass-vms-with-ansible-a84cdd7bcbe8)):
its `multipass_vm` / `multipass_vm_info` / `multipass_vm_purge` modules launch and
tear down the VM, and the module's `cloud_init:` parameter injects the host's
default SSH public key so the harness connects over **standard SSH** (not the
collection's `multipass exec` connection plugin). The canonical CI/Molecule
instance is named **`ci-boss-skills`**.

Content and recommendations are grounded in
`ai_docs/ansible_tips_and_tricks.md` (facts tuning, the 2026 testing pyramid,
Molecule v26, CI ephemeral infra, and Apple-Silicon VM drivers) and adapted from
`lunar-claude` (de-coupled from its house choices — `mise`, Infisical-only
secrets, and hard Proxmox coupling become optional/cross-referenced).

## Task Description

Create `plugins/boss-homelab/ansible-dev/` following this repo's plugin
conventions (mirroring `proxmox-infra`, plus `agents/`/`commands/`/`hooks/` from
`templates/plugin-template`): a `plugin.json` manifest, `README.md`, three hooks
(passive `PostToolUse` lint + `Stop`/`SubagentStop` pipeline orchestration), five
subagents, four slash commands, and **eight** model-invoked skills
(`ansible-fundamentals`, `ansible-playbook-design`, `ansible-role-design`,
`ansible-idempotency`, `ansible-secrets`, `ansible-error-handling`,
`ansible-testing`, `ansible-proxmox`) with `reference/` and PEP 723 `uv`-run
`tools/`. Register it in `marketplace.json` and pass `verify-structure.py` + repo
lint/markdown checks.

## Objective

A merge-ready `ansible-dev` plugin that: (1) guides Ansible authoring (fundamentals,
playbooks, roles, idempotency, facts, inventory, vault, uv-pinned execution
environments); (2) teaches a full testing strategy with Docker/Podman +
`delegated` as the fast default loop, **Multipass as the recommended ephemeral
live-VM rung** for provisioning against a real machine (full systemd/SSH/reboot
fidelity, before changes touch real hosts), and Tart/Lima/QEMU documented for
multi-distro Apple-Silicon VM matrices; (3) ships `uv`-based helper tools that produce
machine-readable pass/fail output for the agent harness; (4) drives an orchestrated
multi-agent pipeline (generator → validator → reviewer → debugger) with persistent
state, in which the validator/debugger agents **shell out to the JSON tools** as
the single source of truth; (5) auto-lints Ansible on `PostToolUse` via `uvx
ansible-lint` without colliding with the pipeline hooks.

## Problem Statement

The agent harness writes Ansible but has no built-in, structured way to validate
it locally before applying to homelab hosts. Mistakes (non-idempotent tasks,
deprecated modules, bad inventory, fact-gathering overhead) only surface at apply
time against real machines — a slow, risky loop. There is also no curated,
Apple-Silicon-aware guidance for ephemeral test infrastructure, and no quality
gate (validate → review → fix) that runs to completion before code is considered
done.

## Solution Approach

Build an eight-skill plugin where the *knowledge* lives in progressive-disclosure
`reference/` files and the *feedback loop* lives in `uv`-run Python tools that
return JSON. The headline tool is `tools/test_loop.py` — an orchestrator that runs
lint → syntax/check → Molecule converge → idempotence → verify and returns a
single structured result the harness can act on. `test_loop.py` also gains an
**optional live-VM stage** (`--live` / `--driver multipass`, off by default) that
delegates to `multipass_provision.py` for full-OS-fidelity validation.

The revised testing pyramid the spec documents:

1. **Lint / syntax** — `lint_report.py`, `syntax_check.py`.
2. **Container integration + idempotence** — Molecule Docker/Podman, or
   `delegated` against a static host (fast; the default loop).
3. **Live-VM provisioning (the "real live machine" rung)** — an ephemeral Ubuntu VM
   named **`ci-boss-skills`** launched via the `theko2fi.multipass` collection
   (`multipass_vm` + `cloud_init` SSH-key injection), then the playbook +
   idempotence run against it over **real SSH** (`ansible_connection=ssh`,
   `ansible_user=ubuntu`); full systemd / reboot / sudo fidelity. Two entrypoints
   share this rung: the standalone `multipass_provision.py` tool (harness
   autonomous loop) and the `molecule-multipass` scenario's create/destroy
   playbooks (guided/Molecule loop).
4. **Pre-production** — run against real homelab hosts (`--check`/`--diff` first).

On top of that, layer an orchestrated **multi-agent pipeline**: slash commands
scaffold a role/playbook and initialize a state machine
(`.claude/ansible-dev.local.md`); the main session dispatches `ansible-generator`
→ `ansible-validator` → `ansible-reviewer`, routing through `ansible-debugger` on
failure (max 3 attempts, then escalate). Agents hand off via `.bundle.md` files; a
blocking `Stop` hook prevents the session from ending mid-pipeline and a
`SubagentStop` hook advances state and enforces bundle writes. The **hybrid
bridge**: the validator/debugger agents invoke the JSON tools, so both autonomous
and guided modes share one source of truth.

All CLIs are obtained via `uv tool install ansible-dev-tools` / `uvx` (no system
Python pollution); all plugin scripts are PEP 723 with pinned inline deps.

### Adaptation rules (porting lunar-claude content)

Content fetched from `lunar-claude` via `gh` is a *starting point* and must be
adapted:

- **Generalize away house tooling.** Strip `mise`; use `uv run` / `uvx`
  exclusively (matches `proxmox-infra` and CLAUDE.md).
- **Secrets: vault-first, external optional.** Lead with `ansible-vault` +
  `no_log`; document external lookups (Infisical, HashiCorp Vault) as optional.
- **Proxmox: config-management only.** `ansible-proxmox` covers the
  `community.proxmox` Ansible modules; cross-reference `proxmox-infra` for
  Terraform/OpenTofu provisioning instead of duplicating it.
- **Naming.** State/bundle files use our plugin name:
  `.claude/ansible-dev.local.md` and `.claude/ansible-dev.<phase>.bundle.md`
  (aligns with the repo's documented `.local.md` plugin-settings pattern).
- **Frontmatter.** Agent `.md` files MUST carry `description` **and**
  `capabilities` (required by `scripts/verify-structure.py`); command `.md` files
  MUST carry `description`. SKILL.md keeps `name` + `description`; fold
  lunar-claude's `when_to_use` into the `description` and a **Trigger Phrases**
  section.
- **Hooks must not collide.** Passive lint goes on **`PostToolUse`** (async, on
  `Write`/`Edit` of Ansible files); **`Stop`/`SubagentStop`** are reserved for
  pipeline orchestration.

## Relevant Files

Existing files to follow as patterns or to modify:

- `plugins/boss-homelab/proxmox-infra/skills/proxmox-infrastructure/SKILL.md` —
  gold-standard SKILL.md shape (frontmatter, Trigger Phrases, Available Tools via
  `${CLAUDE_SKILL_DIR}`, "For Details" index). Mirror this.
- `plugins/boss-homelab/proxmox-infra/skills/.../tools/cluster_status.py` — PEP
  723 shebang `#!/usr/bin/env -S uv run --script --quiet`, typed, `--help`.
- `plugins/boss-homelab/proxmox-infra/.claude-plugin/plugin.json` — manifest shape.
- `plugins/boss-dev/agent-harness/agents/*.md` — agent frontmatter shape
  (`name`, `description`, `capabilities`, `tools`, `color`, `model`).
- `plugins/boss-dev/python-dev/commands/debug-ci.md` — command frontmatter shape
  (`description`, `allowed-tools`).
- `.claude-plugin/marketplace.json` — add the new plugin entry (copy
  `proxmox-infra` block, retune fields).
- `templates/plugin-template/` — scaffolds `agents/`, `commands/`, `hooks/`,
  `skills/`; `hooks/hooks.json` shows `${CLAUDE_PLUGIN_ROOT}` wiring.
- `scripts/verify-structure.py` — structure validator to run after scaffolding
  (validates agent `description`+`capabilities`, command `description`, hook
  events/types, `${CLAUDE_PLUGIN_ROOT}` usage).
- `.claude/rules/plugin-structure.md`, `.claude/rules/skill-development.md`,
  `.claude/rules/documentation.md` — binding repo standards (note the GitHub
  #12781 parser bug: never use exclamation-mark + backtick or `@` patterns in
  SKILL.md code blocks; use `$ command` notation).
- `ai_docs/ansible_tips_and_tricks.md` — source material for reference content
  (facts, testing pyramid, Molecule v26, CI ephemeral infra, macOS drivers).
- `basher83/lunar-claude` `plugins/infrastructure/ansible-workflows` — source for
  agents, commands, pipeline hooks, and skill content; fetch via
  `gh api repos/basher83/lunar-claude/contents/...` and apply the Adaptation rules.

### New Files

```text
plugins/boss-homelab/ansible-dev/
├── .claude-plugin/plugin.json
├── README.md
├── hooks/
│   ├── hooks.json                  # PostToolUse async lint; Stop + SubagentStop pipeline
│   ├── check-pipeline-state.py     # Stop: block when active pipeline (PEP 723, deps=[])
│   └── subagent-complete.py        # SubagentStop: validate bundle, advance phase (PEP 723)
├── scripts/lint.sh                 # PostToolUse async lint via uvx ansible-lint (guarded, || true)
├── agents/
│   ├── ansible-orchestrator.md     # sonnet — coordinate phases, manage state/retries
│   ├── ansible-generator.md        # sonnet — author idempotent playbooks/roles
│   ├── ansible-validator.md        # haiku  — run JSON lint/syntax/idempotence tools
│   ├── ansible-reviewer.md         # opus   — 6-dimension scored review report
│   └── ansible-debugger.md         # sonnet — root-cause analysis + fixes
├── commands/
│   ├── create-role.md              # scaffold role tree + init pipeline state/bundle
│   ├── create-playbook.md          # scaffold state-based playbook + init pipeline
│   ├── lint.md                     # run lint_report.py; categorize errors/warnings/info
│   └── analyze.md                  # review|enhance modes; review hands to ansible-reviewer
└── skills/
    ├── ansible-fundamentals/
    │   ├── SKILL.md                 # golden rules, FQCN, module selection, uv run
    │   ├── reference/{golden-rules.md, facts.md, inventory.md, execution-environments.md}
    │   ├── anti-patterns/common-mistakes.md
    │   └── tools/inventory_validate.py        # ansible-inventory --list/--graph -> JSON
    ├── ansible-playbook-design/
    │   ├── SKILL.md                 # state-based present/absent, play structure, imports
    │   └── reference/{state-based-patterns.md, play-structure.md}
    ├── ansible-role-design/
    │   ├── SKILL.md
    │   └── reference/{role-structure-standards.md, variable-management.md,
    │                  handler-best-practices.md, meta-dependencies.md,
    │                  documentation-templates.md}
    ├── ansible-idempotency/
    │   ├── SKILL.md                 # changed_when, failed_when, check-before-create
    │   ├── reference/idempotency-patterns.md
    │   └── tools/idempotence_check.py         # run twice, assert changed==0 -> JSON
    ├── ansible-secrets/
    │   ├── SKILL.md                 # ansible-vault first; no_log; external vaults optional
    │   └── reference/{vault.md, no-log.md, external-vaults.md}
    ├── ansible-error-handling/
    │   ├── SKILL.md                 # block/rescue/always, until/retries, assert/fail
    │   └── reference/error-handling.md
    ├── ansible-testing/
    │   ├── SKILL.md                 # testing pyramid + ansible-lint + review report
    │   ├── reference/{testing-pyramid.md, molecule.md, verifiers.md,
    │   │              ci-ephemeral-infra.md, macos-drivers.md, multipass-lab.md,
    │   │              multipass-collection.md, homelab-targets.md,
    │   │              ansible-lint-config.md, review-report-format.md}
    │   ├── examples/{molecule-docker/molecule.yml, molecule-delegated/molecule.yml,
    │   │             molecule-multipass/{molecule.yml, create.yml, destroy.yml,
    │   │                                converge.yml, requirements.yml},
    │   │             multipass/cloud-init.yaml, testinfra/test_example.py}
    │   ├── workflows/{dev-feedback-loop.md, pre-production-checklist.md}
    │   ├── anti-patterns/testing-mistakes.md
    │   └── tools/{lint_report.py, syntax_check.py, molecule_run.py,
    │             multipass_provision.py, test_loop.py}
    └── ansible-proxmox/
        ├── SKILL.md                 # community.proxmox modules; cross-ref proxmox-infra
        └── reference/{module-index.md, vm-templates.md, cluster-ceph.md, networking.md}
```

## Architecture

### Agents (model-tiered)

| Agent | Model | Trigger | Purpose |
|-------|-------|---------|---------|
| `ansible-orchestrator` | sonnet | "full pipeline", "production-ready", resume | Coordinate phases, manage state + retries |
| `ansible-generator` | sonnet | create-* handoff or explicit "write a playbook/role" | Author idempotent, FQCN-correct code |
| `ansible-validator` | haiku | after generation / "lint this" | Run `lint_report.py` + `syntax_check.py` (+ idempotence); PASS/FAIL bundle |
| `ansible-reviewer` | opus | after validation passes / "review for production" | 6-dimension scored review report |
| `ansible-debugger` | sonnet | validation FAIL or review NEEDS_REWORK | Root-cause analysis + fixes, then re-validate |

**Key insight to document:** subagents cannot spawn subagents — the **main session
is the orchestrator**, dispatching agents based on pipeline state. The "hand off to
X" lines in agent prompts are guidance for the main loop, not executable dispatches
by the subagent.

### Pipeline state contract

State file `$CLAUDE_PROJECT_DIR/.claude/ansible-dev.local.md` frontmatter:
`active` (bool), `pipeline_phase` (scaffolding|generating|validating|reviewing|
debugging|complete), `target_path`, `target_type` (playbook|role), `current_agent`,
`started_at`, `validation_attempts` (int), `last_validation_passed` (bool),
`completed_at`.

Context bundles `$CLAUDE_PROJECT_DIR/.claude/ansible-dev.<phase>.bundle.md`:

| Bundle | Source → Target | Carries |
|--------|-----------------|---------|
| `.scaffolding.bundle.md` | command → generator | requirements, target path/type |
| `.generating.bundle.md` | generator → validator | files created, patterns, validation cmd |
| `.validating.bundle.md` | validator → reviewer/debugger | pass/fail, error list |
| `.reviewing.bundle.md` | reviewer → debugger | required HIGH-severity fixes |
| `.debugging.bundle.md` | debugger → validator | fixes applied, re-validation cmd |

Phase transitions: scaffolding → generating → validating; validating → reviewing
(pass) or → debugging (fail); reviewing → complete (APPROVED) or → debugging
(else); debugging → validating (retry). `validation_attempts >= 3` → block +
escalate to user. State files are auto-appended to `.gitignore` by both the
commands and the hooks (defense in depth).

### Structured review report (ansible-reviewer)

Six dimensions — idempotency, security, structure, performance, maintainability,
proxmox — each scored 0.0–1.0 with a confidence, weighted to an overall rating /5
(security 25%, idempotency 20%, structure/maintainability/performance 15% each,
proxmox 10% when applicable). Recommendation is `APPROVED` /
`APPROVED_WITH_CHANGES` / `NEEDS_REWORK`. Each finding carries `severity`, `file`,
`line`, `issue`, `fix`, `confidence`. Documented in
`ansible-testing/reference/review-report-format.md`.

## Implementation Phases

### Phase 1: Foundation

Scaffold the plugin directory from `templates/plugin-template` (using its
`agents/`, `commands/`, `hooks/` dirs), write `plugin.json`, register in
`marketplace.json`, wire `hooks.json` (PostToolUse lint + Stop/SubagentStop
pipeline) + `scripts/lint.sh`, and stub the two pipeline hook scripts. Get
`verify-structure.py` passing with empty-but-valid skills/agents/commands.

### Phase 2: Skills & tools

Author the eight `SKILL.md` files and all `reference/` content (distilled from
`ai_docs/ansible_tips_and_tricks.md` and adapted from `lunar-claude`), then
implement the PEP 723 tools — JSON output first, with `test_loop.py` as the
keystone.

### Phase 3: Agents, commands & pipeline

Author the five agents (generic Ansible; validator/debugger shell out to the JSON
tools; reviewer emits the structured report), the four commands, and the two
pipeline hook scripts (port + de-house lunar-claude's `check-pipeline-state.py` /
`subagent-complete.py`, renamed to the `ansible-dev.*` state/bundle naming).

### Phase 4: Integration & Polish

Add `examples/`, `workflows/`, `anti-patterns/`; write the README (both modes,
pipeline diagram, agent/command/skill tables, abort instructions, auto-gitignore);
add importlib smoke tests for the tools and hook scripts; run full repo validation
(verify-structure, make lint, markdown-lint, link-check, test) and fix all
findings.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Scaffold plugin skeleton

- Create `plugins/boss-homelab/ansible-dev/` with `.claude-plugin/`, `hooks/`,
  `scripts/`, `agents/`, `commands/`, and the eight
  `skills/<skill>/{reference,tools,...}` directories per the New Files tree.
- Write `plugin.json`: name `ansible-dev`, `displayName` "Ansible Dev",
  version `0.1.0`, MIT, author/homepage/repository matching `proxmox-infra`,
  keywords `[ansible, ansible-lint, molecule, testinfra, testing, idempotency,
  multi-agent, pipeline, homelab, configuration-management, uv, iac]`.

### 2. Register in marketplace

- Add an `ansible-dev` entry to `.claude-plugin/marketplace.json` (category
  `boss-homelab`, `source ./plugins/boss-homelab/ansible-dev`, matching
  description + keywords + author).

### 3. Wire the hooks

- `hooks/hooks.json`:
  - `PostToolUse` (matcher `Write|Edit`) → async
    `bash "${CLAUDE_PLUGIN_ROOT}/scripts/lint.sh"`.
  - `Stop` → `uv run "${CLAUDE_PLUGIN_ROOT}/hooks/check-pipeline-state.py"`.
  - `SubagentStop` → `uv run "${CLAUDE_PLUGIN_ROOT}/hooks/subagent-complete.py"`.
- `scripts/lint.sh`: prefer `uvx ansible-lint` (fallback to PATH `ansible-lint`);
  no-op cleanly when neither is available; scope to Ansible files
  (`*.yml`/`*.yaml`/`ansible.cfg`); never hard-fail the hook (`|| true`).

### 4. Author the eight SKILL.md files

- Each: frontmatter `name` + concrete `description` (fold in `when_to_use`).
- Sections: Trigger Phrases, Available Tools (via `${CLAUDE_SKILL_DIR}`, run with
  `uv run`), Core Capabilities, Quick Examples, "For Details" index linking every
  `reference/`/`tools/`/`examples/`/`workflows/`/`anti-patterns/` file.
- Use `$ command` notation only (parser-bug safe).

### 5. Author reference content per skill

- Apply the Adaptation rules (uv-only, vault-first secrets, Proxmox cross-ref).
- Preserve our unique content: `ansible-fundamentals/reference/facts.md`
  (gather_subset, smart/redis/jsonfile cache, custom facts.d, set_fact/cacheable
  pitfalls), `inventory.md` (homelab patterns: Proxmox VM/LXC, macOS, local,
  docker conn), `execution-environments.md` (pin ansible-core + collections), and
  the testing skill's `macos-drivers.md` / `homelab-targets.md` /
  `testing-pyramid.md`.
- `ansible-testing/reference/multipass-lab.md` (the live-VM rung): install
  (`brew install --cask multipass` preferred, or the official `.pkg`; macOS 13.3+;
  set the QEMU backend on Apple Silicon with `multipass set local.driver=qemu`);
  why/when (full-OS-fidelity rung between containers and real hosts; Ubuntu/Debian
  images match homelab VM/LXC guests; **Ubuntu-only** limitation → use Tart/Lima
  for RHEL/Rocky/Fedora); lifecycle command reference (`launch`, `list`, `info`,
  `exec`, `shell`, `mount`, `transfer`, `stop`/`start`, `delete`, `purge`); the
  **cloud-init + standard-SSH connection model** with a worked inventory +
  cloud-init example (inject the host's default pubkey into the `ubuntu` user,
  connect via `ansible_user=ubuntu` + private key file, passwordless sudo become);
  the canonical CI/Molecule instance name **`ci-boss-skills`**; `multipass_provision.py`
  usage and the dev-loop workflow; ephemeral VM naming + `multipass delete --purge`
  cleanup discipline; cross-refs to `multipass-collection.md`, `macos-drivers.md`
  (Molecule matrix), and `homelab-targets.md`.
- `ansible-testing/reference/multipass-collection.md` (the Ansible-native driver):
  the `theko2fi.multipass` collection as the **recommended** way to drive the
  Multipass rung from Ansible/Molecule instead of the sparsely-maintained
  `molecule-multipass` pip driver. Cover: install via `ansible-galaxy collection
  install theko2fi.multipass` / a `requirements.yml`; the module set (`multipass_vm`,
  `multipass_vm_info`, `multipass_vm_exec`, `multipass_vm_purge`,
  `multipass_vm_transfer_into`, `multipass_mount`); `multipass_vm` options
  (`name`, `image` default `ubuntu-lts`, `cpus`, `memory`, `disk`, `state`
  present|started|absent|stopped, and **`cloud_init:` — a path or URL to user-data**);
  the SSH-key-injection pattern (render a `#cloud-config` with the host pubkey to a
  temp file, pass it as `cloud_init:`, launch `name: ci-boss-skills`, read the VM IP
  via `multipass_vm_info`, then connect over **standard SSH**); an explicit note that
  the collection **also** ships a `theko2fi.multipass.multipass` connection plugin
  that tunnels via `multipass exec` (no SSH) — we deliberately prefer real SSH for
  homelab fidelity, but document the connection plugin as an alternative for hosts
  with no reachable IP. Link the Medium walkthrough and the Galaxy/GitHub docs.

### 6. Implement PEP 723 JSON tools

- `ansible-fundamentals/tools/inventory_validate.py`
  (`ansible-inventory --list`/`--graph`).
- `ansible-idempotency/tools/idempotence_check.py` (run playbook twice; assert
  second run `changed==0`).
- `ansible-testing/tools/`: `lint_report.py` (yamllint + ansible-lint),
  `syntax_check.py` (`--syntax-check` + `--check` dry run), `molecule_run.py` (run
  a scenario; parse converge/idempotence/verify phases), and `test_loop.py`
  (orchestrate lint → syntax/check → molecule converge → idempotence → verify, with
  an optional `--live`/`--driver multipass` stage delegating to
  `multipass_provision.py`).
- `ansible-testing/tools/multipass_provision.py` (the live-VM rung): shells out to
  `multipass` and `ansible-playbook` (does not import them).
  - **CLI:** `--playbook <path>` (required); `--name <vm>` (**default `ci-boss-skills`**),
    `--image <24.04>`, `--cpus`, `--mem`, `--disk`,
    `--ssh-key <path>` (default: autodetect `~/.ssh/id_ed25519.pub` then
    `~/.ssh/id_rsa.pub`; error with remediation if neither exists — never hardcode a
    key), `--idempotence` (run twice, assert second run `changed==0`), `--keep`
    (skip teardown), `--extra-args`, `--json`.
  - **Phases (each a JSON entry):** preflight (is `multipass` installed? → clean
    no-op + remediation if not; resolve the SSH pubkey) → launch (generate a
    `#cloud-config` that writes the host pubkey to the default `ubuntu` user's
    `ssh_authorized_keys` + passwordless sudo, then `multipass launch --name
    ci-boss-skills --cloud-init <file>`; if a stale VM of that name exists, delete
    `--purge` it first so re-runs are deterministic) → wait-ready + resolve VM IP
    (`multipass info --format json`) → write a temp inventory
    (`<name> ansible_host=<ip> ansible_user=ubuntu ansible_connection=ssh
    ansible_ssh_private_key_file=<key without .pub>`) → converge
    (`ansible-playbook -i <inv>`) → optional idempotence run → verify → teardown
    (`multipass delete <name> --purge`) in a `try/finally` unless `--keep`.
  - **JSON:** `{ok, vm_name, image, ip, phases:[{name, ok, summary}], idempotent,
    kept, remediation}`. Teardown is guaranteed even on failure (finally) — no
    orphaned VMs.
- Each: `from __future__ import annotations`, full types, `argparse` with `--help`,
  `--json` structured output with `{ok, errors[], summary, remediation}`,
  side-effect-free import via `__main__` guard.

### 7. Author the five agents

- `description` + `capabilities` frontmatter (required), plus `model`, `tools`,
  `skills`, `color`. Models per the agent table.
- `ansible-validator` and `ansible-debugger` invoke the JSON tools (hybrid bridge)
  and record results into their bundles.
- `ansible-reviewer` emits the 6-dimension scored report.
- Document the "subagents can't spawn subagents — main session orchestrates"
  insight in `ansible-orchestrator`.

### 8. Author the four commands

- `description` + `allowed-tools` + `argument-hint` + `model` frontmatter.
- `create-role` / `create-playbook`: scaffold structure, then initialize the state
  file + `.scaffolding.bundle.md` + `.gitignore` patterns, then hand off to
  `ansible-generator`.
- `lint`: run `lint_report.py`, categorize errors/warnings/info with fix guidance.
- `analyze`: `review` mode (hand findings to `ansible-reviewer`) and `enhance` mode
  (forward-looking roadmap).

### 9. Port + de-house the pipeline hook scripts

- `check-pipeline-state.py` (Stop): block when an active pipeline exists; emit
  next-agent guidance; escalate at `validation_attempts >= 3`; no-op (`{}`) when no
  state file or `active: false`.
- `subagent-complete.py` (SubagentStop): validate the current agent wrote its
  bundle; advance `pipeline_phase` + `current_agent`; on validator, read
  `validation_passed` from the bundle to branch reviewing/debugging; on reviewer,
  complete on APPROVED.
- Both: rename state/bundle files to `ansible-dev.*`, auto-append `.gitignore`.

### 10. Add examples, workflows, anti-patterns, README

- Minimal runnable `examples/` (molecule-docker, molecule-delegated,
  molecule-multipass, testinfra test).
- `examples/molecule-multipass/`: a **delegated-driver** scenario that owns the VM
  lifecycle with the `theko2fi.multipass` collection (not the stale
  `molecule-multipass` pip driver). Ships:
  - `requirements.yml` — `collections: [{name: theko2fi.multipass, version: ">=0.4.0"},
    {name: community.general}]` (resolved by molecule's `dependency: galaxy`).
  - `molecule.yml` — `driver.name: default`, one platform `name: ci-boss-skills`,
    `provisioner.name: ansible`, `verifier.name: testinfra`.
  - `create.yml` — render a `#cloud-config` containing the host pubkey
    (`lookup('file', ssh_pubkey_path)`, path from `MOLECULE_SSH_PUBKEY` env or
    autodetected) to `molecule_ephemeral_directory`; `theko2fi.multipass.multipass_vm`
    with `name: ci-boss-skills`, `image: 24.04`, `cloud_init: <rendered file>`,
    `state: started`; `theko2fi.multipass.multipass_vm_info` to read the IP; then
    `add_host` with `ansible_connection: ssh`, `ansible_user: ubuntu`,
    `ansible_ssh_private_key_file: <key without .pub>`.
  - `destroy.yml` — `theko2fi.multipass.multipass_vm name: ci-boss-skills state: absent`
    followed by `theko2fi.multipass.multipass_vm_purge` (guaranteed cleanup).
  - `converge.yml` — import the role/playbook under test.
  - A header note: Ubuntu-only; connects over real SSH; complements (does not
    replace) the standalone `multipass_provision.py` autonomous loop.
- `examples/multipass/cloud-init.yaml`: worked `#cloud-config` that injects the host
  SSH pubkey into the default `ubuntu` user (`ssh_authorized_keys`), disables SSH
  password auth (`ssh_pwauth: false`), and grants passwordless sudo — the exact
  connection model both `multipass_provision.py` and `create.yml` generate — with
  the matching `ci-boss-skills` inventory snippet. Uses a placeholder pubkey (a real
  key is rendered at runtime, never committed).
- `workflows/`: `dev-feedback-loop.md` (show the Docker → Multipass live-VM →
  real-host progression), `pre-production-checklist.md`. `anti-patterns/` for
  fundamentals + testing.
- `README.md` (required): both modes, pipeline diagram, agent/command/skill
  tables, `uv tool install ansible-dev-tools` requirements, hook behavior, abort
  via `active: false`, auto-gitignore, install.

### 11. Add smoke tests

- In `tests/`, load each new PEP 723 tool **and** the two hook scripts via
  `importlib.util.spec_from_file_location` (repo pattern) to assert importability
  and presence of a callable entry point. No trivial tests beyond this.

### 12. Validate everything

- Run `scripts/verify-structure.py` (and `--strict`), `make lint`,
  `make markdown-lint`, `make link-check`, and `make test`; fix every finding
  until clean.

## Improvement Areas Identified

Beyond the original spec, this pass surfaced the following gaps to close during
implementation:

1. **Prefer the `theko2fi.multipass` collection over `molecule-multipass`.** The
   `ai_docs` guidance (Option 4) reaches for the `molecule-multipass` pip driver,
   which is sparsely maintained and pins older Molecule. Standardize on the
   collection + Molecule's `default` (delegated) driver with `create.yml`/`destroy.yml`.
   Update `ai_docs/ansible_tips_and_tricks.md` Option 4 to cross-reference
   `multipass-collection.md` rather than leaving the stale recommendation
   authoritative.
2. **Connection model must be SSH, not `multipass exec`.** The collection ships a
   `theko2fi.multipass.multipass` connection plugin that tunnels via `multipass
   exec` — convenient but *not* SSH, so it hides real auth/network behavior. The
   user requirement is genuine SSH: create the VM with the collection + inject the
   pubkey via `cloud_init`, then connect with `ansible_connection=ssh`. Document the
   exec plugin only as a fallback.
3. **SSH key resolution, never hardcoded.** Both entrypoints must autodetect the
   host default pubkey (`id_ed25519.pub` → `id_rsa.pub`), fail with actionable
   remediation if absent, and honor an override (`--ssh-key` / `MOLECULE_SSH_PUBKEY`).
   The committed `cloud-init.yaml` uses a placeholder; the real key is templated at
   runtime and never committed.
4. **Deterministic instance name + collision handling.** The CI/Molecule instance is
   `ci-boss-skills`. Because that name is stable (not random), launch must delete any
   pre-existing `ci-boss-skills` (`--purge`) before creating, and teardown must run
   in `finally` / molecule `destroy` even on failure — no orphaned VMs, no
   "instance already exists" flakes.
5. **Add a Galaxy `requirements.yml`.** The spec had no collection-requirements
   file; molecule's `dependency: galaxy` and local runs need one pinning
   `theko2fi.multipass` (+ `community.general`, `community.docker` as used).
6. **CI feasibility of the Multipass rung.** The `ci-boss-skills` name implies CI,
   but GitHub-hosted macOS runners cannot reliably nest Multipass VMs (nested-virt
   limits). Document that the Multipass rung targets **local dev and self-hosted
   runners**; keep Docker/Podman + `delegated` as the hosted-CI default. Fold this
   into `ci-ephemeral-infra.md`.
7. **Apple-Silicon backend note.** Record `multipass set local.driver=qemu` (and
   macOS 13.3+) in `multipass-lab.md`; the default VZ backend has cloud-init/mount
   quirks that break the key-injection flow.
8. **New-plugin publish parity.** Adding `ansible-dev` is a new `plugins[]` entry;
   `plugin.json.version` and `marketplace.json[].version` must match at `0.1.0` and
   pass `verify-structure.py --strict` (the `version-bump-reviewer` skill validates
   this as an initial publish, not a bump).

## Testing Strategy

- **Structure**: `scripts/verify-structure.py` must pass (manifest schema, SKILL.md
  frontmatter for 8 skills, agent frontmatter `description`+`capabilities` on all
  5, command frontmatter `description` on all 4, hook event/type validity,
  `${CLAUDE_PLUGIN_ROOT}` usage, marketplace parity).
- **Python**: `make lint` (ruff + basedpyright) clean on the new tools + hook
  scripts; `make test` runs importlib smoke tests (PEP 723 scripts import without
  side effects via `__main__` guard).
- **Markdown**: `make markdown-lint` (rumdl) and `make link-check` (lychee) clean.
- **Tool behavior (manual)**: against a throwaway sample role —
  `uv run .../tools/lint_report.py --json`, `syntax_check.py`,
  `idempotence_check.py`, and `test_loop.py` should each emit valid JSON with a
  correct top-level `ok` boolean for both passing and intentionally-broken input.
- **Live-VM (manual)**: against a sample playbook,
  `uv run .../tools/multipass_provision.py --playbook ... --idempotence --json`
  launches the `ci-boss-skills` Ubuntu VM (cloud-init injects the host pubkey),
  connects over **SSH** as `ubuntu`, runs the play (+ idempotence), tears it down
  (`multipass list` shows no leftover `ci-boss-skills`), and emits valid `{ok:...}`
  JSON; with `multipass` absent it returns a clean no-op + remediation (top-level
  `ok:false`, preflight phase failed) and creates no VM; re-running when a stale
  `ci-boss-skills` exists recreates cleanly rather than erroring.
- **Molecule live-VM (manual)**: in `examples/molecule-multipass/`,
  `molecule test` resolves `theko2fi.multipass` via `requirements.yml`, `create.yml`
  launches `ci-boss-skills` with cloud-init SSH-key injection, `converge`/`verify`
  run over SSH, and `destroy.yml` (`multipass_vm state=absent` + `multipass_vm_purge`)
  leaves no VM behind even on failure.
- **Hook (manual)**: `scripts/lint.sh` no-ops gracefully when `ansible-lint`/`uvx`
  is absent and lints when present; `check-pipeline-state.py` returns `{}` with no
  state file and `{"decision":"block", ...}` when a pipeline is active;
  `subagent-complete.py` advances `pipeline_phase` and reminds on a missing bundle.
  Feed each synthetic JSON on stdin.

## Acceptance Criteria

- `plugins/boss-homelab/ansible-dev/` exists with manifest, README, three hooks,
  four commands, five agents, and **eight** skills with appropriate
  `reference/`/`tools/`/`examples/`/`workflows/`/`anti-patterns/`.
- `ansible-dev` is registered in `marketplace.json` with matching version/keywords.
- All helper tools + hook scripts are PEP 723, run via `uv`, typed; tools emit
  structured JSON with a top-level `ok` flag; `test_loop.py` orchestrates the full
  pyramid.
- Validator/debugger agents invoke the JSON tools (hybrid bridge); reviewer emits
  the 6-dimension scored report with APPROVED/APPROVED_WITH_CHANGES/NEEDS_REWORK.
- Pipeline works end-to-end: a `create-*` command initializes
  `.claude/ansible-dev.local.md`; `Stop` blocks while `active: true`;
  `SubagentStop` advances phase + enforces bundles; retry capped at 3.
- Passive `PostToolUse` lint runs async on Ansible `Write`/`Edit` without colliding
  with the pipeline hooks.
- Testing skill recommends Docker/Podman + `delegated` as the fast default and
  documents Apple-Silicon VM drivers and homelab-target→driver mapping;
  `ansible-secrets` is vault-first; `ansible-proxmox` cross-references
  `proxmox-infra` (no Terraform duplication); no `mise`/Infisical-required
  assumptions.
- Testing skill ships `multipass-lab.md`, `multipass-collection.md`,
  `multipass_provision.py` (full VM lifecycle, cloud-init SSH-key injection over
  **real SSH**, `{ok:...}` JSON, guaranteed `try/finally` teardown), and a
  `molecule-multipass` example that drives the VM via the **`theko2fi.multipass`**
  collection (`create.yml`/`destroy.yml`, `requirements.yml`) rather than the stale
  `molecule-multipass` pip driver; the canonical instance is named **`ci-boss-skills`**
  and connects as `ubuntu` over SSH. Multipass is positioned as the **ephemeral
  live-VM rung** for provisioning against a real machine (not the multi-distro
  matrix path, which stays with Tart/Lima), with its Ubuntu-only limitation stated.
- No exclamation-mark + backtick / `@` patterns in any SKILL.md (parser-bug safe).
- `verify-structure.py`, `make lint`, `make markdown-lint`, `make link-check`,
  and `make test` all pass.

## Validation Commands

- `uv run scripts/verify-structure.py` (and `--strict`) — validate marketplace +
  plugin structure incl. agents/commands frontmatter.
- `make lint` — ruff + basedpyright (auto-fixes formatting/imports) on new tools +
  hook scripts.
- `make test` — run importlib smoke tests for the new PEP 723 scripts + hooks.
- `make markdown-lint` — rumdl on new markdown.
- `make link-check` — lychee on new markdown links.
- `uv run plugins/boss-homelab/ansible-dev/skills/ansible-testing/tools/test_loop.py --help`
  — confirm the keystone tool loads and exposes its interface.
- `uv run plugins/boss-homelab/ansible-dev/skills/ansible-testing/tools/multipass_provision.py --help`
  — confirm the live-VM tool loads and exposes its interface.
- `echo '{"cwd":"/tmp/x"}' | uv run plugins/boss-homelab/ansible-dev/hooks/check-pipeline-state.py`
  — returns `{}` with no state file (no-op safety).

## Notes

- **Category**: `boss-homelab` (pairs with `proxmox-infra`; homelab-focused).
- **uv strategy** (confirmed): CLIs via `uv tool install ansible-dev-tools` /
  `uvx`; plugin scripts are PEP 723 `uv run --script` with pinned inline deps
  (e.g. `["rich"]` for output; shell out to `ansible`/`molecule`/`ansible-lint`
  rather than importing them). An `execution-environments.md` reference documents
  pinning `ansible-core` + collections for reproducibility.
- **Scope** (confirmed): Ansible-only. Terraform/OpenTofu remains in
  `proxmox-infra`; cross-reference it from `ansible-proxmox`/`ansible-testing`
  rather than duplicating.
- **Test-driver split** (confirmed): three complementary tiers —
  Docker/Podman + `delegated` (fast default inner loop); **Multipass (the ephemeral
  live-VM sandbox — Ubuntu-only, matching homelab VM/LXC guests; QEMU backend
  (`multipass set local.driver=qemu`); `brew install --cask multipass`; instance
  `ci-boss-skills`; SSH via cloud-init key injection for real-host fidelity)** for
  provisioning against a real machine; Tart/Lima for multi-distro (RHEL/Rocky/Fedora)
  VM matrices. `multipass_provision.py` owns the standalone live-VM loop; the
  `molecule-multipass` scenario covers the in-Molecule path and drives the VM with
  the `theko2fi.multipass` Ansible collection (`multipass_vm` + `cloud_init`).
- **Hybrid design** (confirmed): two modes share one plugin — autonomous
  JSON-tool self-correction (our differentiator from upstream `lunar-claude`,
  which ships content + agents but no machine-readable tool layer) **and** the
  guided multi-agent pipeline (adapted from `lunar-claude`). The
  validator/debugger agents bridge them by invoking the JSON tools.
- **Agent-harness focus**: every tool's JSON includes per-stage pass/fail, file +
  line of failures where available, and a short remediation hint so the harness
  can self-correct.
- **Source material**: `ai_docs/ansible_tips_and_tricks.md` +
  `basher83/lunar-claude` `ansible-workflows` (fetch via
  `gh api repos/basher83/lunar-claude/contents/...` during implementation, then
  apply the Adaptation rules). Multipass rung grounded in the
  [`theko2fi/ansible-multipass-collection`](https://github.com/theko2fi/ansible-multipass-collection)
  (Galaxy: `theko2fi.multipass`) and its walkthrough,
  [Manage your Multipass VMs with Ansible](https://theko2fi.medium.com/manage-your-multipass-vms-with-ansible-a84cdd7bcbe8).
  Key facts: modules `multipass_vm` (options `name`, `image` [default `ubuntu-lts`],
  `cpus`, `memory`, `disk`, `state`, **`cloud_init`** [path/URL to user-data]),
  `multipass_vm_info`, `multipass_vm_exec`, `multipass_vm_purge`,
  `multipass_vm_transfer_into`, `multipass_mount`; plus a `multipass` connection
  plugin (used only as an SSH fallback).
