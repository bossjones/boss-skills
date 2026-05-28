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

The intended outcome: the agent harness can lint, syntax-check, run Molecule
scenarios, prove idempotency, and run a full layered test loop — all through
helper scripts that emit **structured JSON** so the harness can parse results,
self-correct, and make better decisions without a human in the loop. Content and
recommendations are grounded in `ai_docs/ansible_tips_and_tricks.md` (facts
tuning, the 2026 testing pyramid, Molecule v26, CI ephemeral infra, and
Apple-Silicon VM drivers).

## Task Description

Create `plugins/boss-homelab/ansible-dev/` following this repo's plugin
conventions (mirroring `proxmox-infra`): a `plugin.json` manifest, `README.md`,
an async lint hook, and two model-invoked skills (`ansible-development`,
`ansible-testing`) each with `reference/`, `examples/`, `workflows/`,
`anti-patterns/`, and PEP 723 `uv`-run `tools/`. Register it in
`marketplace.json` and pass `verify-structure.py` + repo lint/markdown checks.

## Objective

A merge-ready `ansible-dev` plugin that: (1) guides Ansible authoring (playbooks,
roles, inventory, facts, vault, uv-pinned execution environments); (2) teaches a
full testing strategy with Docker/Podman + `delegated` as the recommended default
and Tart/Lima/QEMU/Multipass documented for Apple-Silicon VM testing; (3) ships
`uv`-based helper tools that produce machine-readable pass/fail output for the
agent harness; (4) auto-lints Ansible on `Stop`/`SubagentStop` via `uvx
ansible-lint`.

## Problem Statement

The agent harness writes Ansible but has no built-in, structured way to validate
it locally before applying to homelab hosts. Mistakes (non-idempotent tasks,
deprecated modules, bad inventory, fact-gathering overhead) only surface at apply
time against real machines — a slow, risky loop. There is also no curated,
Apple-Silicon-aware guidance for ephemeral test infrastructure.

## Solution Approach

Build a two-skill plugin where the *knowledge* lives in progressive-disclosure
`reference/` files and the *feedback loop* lives in `uv`-run Python tools that
return JSON. The headline deliverable is `tools/test_loop.py` — an orchestrator
that runs lint → syntax/check → Molecule converge → idempotence → verify and
returns a single structured result the harness can act on. An async lint hook
gives passive, continuous feedback during authoring. All CLIs are obtained via
`uv tool install ansible-dev-tools` / `uvx` (no system Python pollution); all
plugin scripts are PEP 723 with pinned inline deps.

## Relevant Files

Existing files to follow as patterns or to modify:

- `plugins/boss-homelab/proxmox-infra/skills/proxmox-infrastructure/SKILL.md` —
  gold-standard SKILL.md shape (frontmatter, Trigger Phrases, Available Tools via
  `${CLAUDE_SKILL_DIR}`, "For Details" index). Mirror this.
- `plugins/boss-homelab/proxmox-infra/skills/.../tools/cluster_status.py` — PEP
  723 shebang `#!/usr/bin/env -S uv run --script --quiet`, typed, `--help`.
- `plugins/boss-homelab/proxmox-infra/.claude-plugin/plugin.json` — manifest shape.
- `.claude-plugin/marketplace.json` — add the new plugin entry (copy
  `proxmox-infra` block, retune fields).
- `templates/plugin-template/hooks/hooks.json` — hook wiring with
  `${CLAUDE_PLUGIN_ROOT}`.
- `scripts/verify-structure.py` — structure validator to run after scaffolding.
- `.claude/rules/plugin-structure.md`, `.claude/rules/skill-development.md`,
  `.claude/rules/documentation.md` — binding repo standards (note the GitHub
  #12781 parser bug: never use exclamation-mark + backtick or `@` patterns in
  SKILL.md code blocks; use `$ command` notation).
- `ai_docs/ansible_tips_and_tricks.md` — source material for reference content
  (facts, testing pyramid, Molecule v26, CI ephemeral infra, macOS drivers).

### New Files

```text
plugins/boss-homelab/ansible-dev/
├── .claude-plugin/plugin.json
├── README.md
├── hooks/hooks.json                      # Stop + SubagentStop -> async lint
├── scripts/lint.sh                       # uvx ansible-lint, guarded + scoped
└── skills/
    ├── ansible-development/
    │   ├── SKILL.md
    │   ├── reference/
    │   │   ├── facts.md                   # gather_subset, smart/redis/jsonfile cache,
    │   │   │                              #   custom facts.d, set_fact/cacheable pitfalls, set_stats
    │   │   ├── playbooks.md               # structure, handlers, validate:, idempotency, FQCN
    │   │   ├── roles.md                   # layout, defaults vs vars, meta deps, galaxy init
    │   │   ├── inventory.md               # static/dynamic, group_vars/host_vars, precedence,
    │   │   │                              #   connection vars (ssh/winrm/local/docker), homelab patterns
    │   │   ├── vault.md                   # ansible-vault, no_log, secret handling
    │   │   └── execution-environments.md  # uv tool install ansible-dev-tools; pin ansible-core + collections
    │   ├── anti-patterns/common-mistakes.md
    │   ├── examples/
    │   │   ├── playbook-with-facts/site.yml
    │   │   └── role-skeleton/             # ansible-galaxy init output, trimmed
    │   ├── workflows/new-role.md
    │   └── tools/
    │       ├── lint_report.py             # yamllint + ansible-lint -> JSON summary
    │       ├── syntax_check.py            # ansible-playbook --syntax-check + --check -> JSON
    │       └── inventory_validate.py      # ansible-inventory --list/--graph -> JSON
    └── ansible-testing/
        ├── SKILL.md
        ├── reference/
        │   ├── testing-pyramid.md         # lint/syntax/unit/integration/idempotency/e2e
        │   ├── molecule.md                # Molecule v26 scenario layout, converge/verify/idempotence
        │   ├── verifiers.md               # ansible verifier vs testinfra+pytest
        │   ├── ci-ephemeral-infra.md      # docker/podman, kind, vagrant, cloud VMs, delegated
        │   ├── macos-drivers.md           # Tart, Lima, molecule-qemu, Multipass, VMware (Apple Silicon)
        │   └── homelab-targets.md         # delegated driver vs physical/macos/proxmox-vm/lxc/docker-on-vm
        ├── anti-patterns/testing-mistakes.md
        ├── examples/
        │   ├── molecule-docker/molecule.yml
        │   ├── molecule-delegated/molecule.yml
        │   └── testinfra/test_example.py
        ├── workflows/
        │   ├── dev-feedback-loop.md       # the tight loop the harness should follow
        │   └── pre-production-checklist.md
        └── tools/
            ├── molecule_run.py            # run scenario, parse converge/idempotence/verify -> JSON
            ├── idempotence_check.py       # run playbook twice, assert changed==0 -> JSON
            └── test_loop.py               # orchestrate full pyramid -> single structured result
```

## Implementation Phases

### Phase 1: Foundation

Scaffold the plugin directory from `templates/plugin-template`, write
`plugin.json`, register in `marketplace.json`, and wire the lint hook +
`scripts/lint.sh`. Get `verify-structure.py` passing with empty-but-valid skills.

### Phase 2: Core Implementation

Author both `SKILL.md` files and all `reference/` content (distilled from
`ai_docs/ansible_tips_and_tricks.md`), then implement the PEP 723 tools — JSON
output first, with `test_loop.py` as the keystone.

### Phase 3: Integration & Polish

Add `examples/`, `workflows/`, `anti-patterns/`; write the README; add importlib
smoke tests for the tools; run full repo validation (verify-structure, make lint,
markdown-lint, link-check) and fix all findings.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Scaffold plugin skeleton

- Create `plugins/boss-homelab/ansible-dev/` with `.claude-plugin/`, `hooks/`,
  `scripts/`, and `skills/ansible-development|ansible-testing/{reference,examples,workflows,anti-patterns,tools}/`.
- Write `plugin.json`: name `ansible-dev`, `displayName` "Ansible Dev",
  version `0.1.0`, MIT, author/homepage/repository matching `proxmox-infra`,
  keywords `[ansible, ansible-lint, molecule, testinfra, testing, homelab,
  configuration-management, idempotency, uv, iac]`.

### 2. Register in marketplace

- Add an `ansible-dev` entry to `.claude-plugin/marketplace.json` (category
  `boss-homelab`, `source ./plugins/boss-homelab/ansible-dev`, matching
  description + keywords + author).

### 3. Wire the lint hook

- `hooks/hooks.json`: `Stop` and `SubagentStop` each run
  `bash "${CLAUDE_PLUGIN_ROOT}/scripts/lint.sh"` with `"async": true`.
- `scripts/lint.sh`: prefer `uvx ansible-lint` (fallback to PATH `ansible-lint`);
  no-op cleanly when neither is available; scope to Ansible files
  (`*.yml`/`*.yaml`/`ansible.cfg`); never hard-fail the hook (`|| true`).

### 4. Write ansible-development SKILL.md

- Frontmatter `name: ansible-development` + concrete `description`.
- Sections: Trigger Phrases, Available Tools (via `${CLAUDE_SKILL_DIR}`, run with
  `uv run`), Core Capabilities, Quick Examples, "For Details" index linking every
  `reference/`/`examples/`/`workflows/`/`anti-patterns/` file.
- Use `$ command` notation only (parser-bug safe).

### 5. Write ansible-development reference content

- `facts.md`, `playbooks.md`, `roles.md`, `inventory.md`, `vault.md`,
  `execution-environments.md` — distilled from `ai_docs` + han examples, with
  homelab-specific inventory patterns (Proxmox VM/LXC, macOS, local, docker conn).

### 6. Implement ansible-development tools (PEP 723, JSON output)

- `lint_report.py` (yamllint + ansible-lint), `syntax_check.py`
  (`--syntax-check` + `--check` dry run), `inventory_validate.py`
  (`ansible-inventory --list`/`--graph`). Each: `from __future__ import
  annotations`, full types, `argparse` with `--help`, `--json` structured output
  with `{ok, errors[], summary}`, side-effect-free import via `__main__` guard.

### 7. Write ansible-testing SKILL.md + reference content

- SKILL.md mirroring step 4 shape, oriented to the testing pyramid.
- `reference/`: `testing-pyramid.md`, `molecule.md`, `verifiers.md`,
  `ci-ephemeral-infra.md`, `macos-drivers.md`, `homelab-targets.md`. Recommend
  **Docker/Podman + `delegated`** as default; document Tart/Lima/QEMU/Multipass
  for Apple-Silicon VM fidelity; map each homelab target type to a driver.

### 8. Implement ansible-testing tools (PEP 723, JSON output)

- `idempotence_check.py` (run playbook twice; assert second run `changed==0`),
  `molecule_run.py` (run a scenario; parse converge/idempotence/verify phases),
  and `test_loop.py` (orchestrate lint → syntax/check → molecule converge →
  idempotence → verify; emit one machine-readable result with per-stage
  pass/fail + remediation hints for the agent harness).

### 9. Add examples, workflows, anti-patterns, README

- Minimal runnable `examples/` (playbook-with-facts, role-skeleton,
  molecule-docker, molecule-delegated, testinfra test).
- `workflows/`: `new-role.md`, `dev-feedback-loop.md`,
  `pre-production-checklist.md`. `anti-patterns/` for both skills.
- `README.md` (required): features, `uv tool install ansible-dev-tools`
  requirements, skills list, hook behavior, install.

### 10. Add smoke tests

- In `tests/`, load each new PEP 723 tool via
  `importlib.util.spec_from_file_location` (repo pattern) to assert importability
  and presence of a callable entry point. No trivial tests beyond this.

### 11. Validate everything

- Run `scripts/verify-structure.py`, `make lint`, `make markdown-lint`,
  `make link-check`, and `make test`; fix every finding until clean.

## Testing Strategy

- **Structure**: `scripts/verify-structure.py` must pass (manifest schema,
  SKILL.md frontmatter, component placement, marketplace parity).
- **Python**: `make lint` (ruff + basedpyright) clean on the new tools;
  `make test` runs importlib smoke tests (PEP 723 scripts import without side
  effects via `__main__` guard).
- **Markdown**: `make markdown-lint` (rumdl) and `make link-check` (lychee) clean.
- **Tool behavior (manual)**: against a throwaway sample role —
  `uv run .../tools/lint_report.py --json`, `syntax_check.py`,
  `idempotence_check.py`, and `test_loop.py` should each emit valid JSON with a
  correct top-level `ok` boolean for both passing and intentionally-broken input.
- **Hook**: confirm `scripts/lint.sh` no-ops gracefully when `ansible-lint`/`uvx`
  is absent and lints when present.

## Acceptance Criteria

- `plugins/boss-homelab/ansible-dev/` exists with manifest, README, hook, and two
  skills, each with `reference/`, `examples/`, `workflows/`, `anti-patterns/`,
  `tools/`.
- `ansible-dev` is registered in `marketplace.json` with matching version/keywords.
- All helper tools are PEP 723, run via `uv`, typed, and emit structured JSON with
  a top-level `ok` flag; `test_loop.py` orchestrates the full pyramid.
- Lint hook runs `ansible-lint` via `uvx` async on `Stop`/`SubagentStop`.
- Testing skill recommends Docker/Podman + `delegated` and documents
  Apple-Silicon VM drivers and homelab-target→driver mapping.
- No exclamation-mark + backtick / `@` patterns in any SKILL.md (parser-bug safe).
- `verify-structure.py`, `make lint`, `make markdown-lint`, `make link-check`,
  and `make test` all pass.

## Validation Commands

- `uv run scripts/verify-structure.py` — validate marketplace + plugin structure.
- `make lint` — ruff + basedpyright (auto-fixes formatting/imports) on new tools.
- `make test` — run importlib smoke tests for the new PEP 723 scripts.
- `make markdown-lint` — rumdl on new markdown.
- `make link-check` — lychee on new markdown links.
- `uv run plugins/boss-homelab/ansible-dev/skills/ansible-testing/tools/test_loop.py --help`
  — confirm the keystone tool loads and exposes its interface.

## Notes

- **Category**: `boss-homelab` (pairs with `proxmox-infra`; homelab-focused).
- **uv strategy** (confirmed): CLIs via `uv tool install ansible-dev-tools` /
  `uvx`; plugin scripts are PEP 723 `uv run --script` with pinned inline deps
  (e.g. `["rich"]` for output; shell out to `ansible`/`molecule`/`ansible-lint`
  rather than importing them). An `execution-environments.md` reference documents
  pinning `ansible-core` + collections for reproducibility.
- **Scope** (confirmed): Ansible-only. Terraform/OpenTofu remains in
  `proxmox-infra`; cross-reference it from `ansible-testing` rather than
  duplicating.
- **Agent-harness focus**: every tool's JSON includes per-stage pass/fail, file +
  line of failures where available, and a short remediation hint so the harness
  can self-correct. This is the core differentiator from the upstream `han` plugin
  (which only ships content + a lint hook).
