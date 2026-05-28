# Plan: terraform-dev plugin

## Context

This adds a new Claude Code plugin, **`terraform-dev`**, to the `boss-skills`
marketplace. The user develops OpenTofu/Terraform for a homelab from an Apple
Silicon Mac and wants the agent harness to *author* and — critically — *test*
infrastructure-as-code with a tight, mostly-hermetic feedback loop **before** any
change touches real resources.

Two things prompted this design:

1. **A scope boundary the plugin must enforce.** OpenTofu/Terraform is only for
   resources with a real lifecycle it **creates and destroys** — Proxmox VMs, LXC
   containers, Docker containers. It is **not** for configuring machines that
   already exist (physical Linux/macOS boxes). The rule is *"OpenTofu provisions,
   Ansible configures"*: the plugin hands off to the `ansible-dev` plugin via
   cloud-init or a generated inventory, and treats `null_resource` /
   `terraform_data` + `remote-exec` provisioners as an anti-pattern.

2. **A layered, agent-driven test loop.** Static checks → plan-based native tests
   → mocked unit tests run freely and can't mutate anything (the hermetic inner
   loop the agent iterates against); apply-based integration and Terratest run
   only against disposable, pool-scoped infra behind an explicit gate.

`terraform-dev` is the **general** TF/OpenTofu development plugin (any target;
default providers `bpg/proxmox` and `kreuzwerker/docker`). It is the sibling of
the already-spec'd `ansible-dev` plugin (`specs/ansible-dev-plugin.md`), which it
mirrors structurally. The existing `proxmox-infra` plugin is retuned to be the
**pve1-specific** host-operations plugin (proxmoxer / cluster / Ansible
`community.general.proxmox`), dropping its general-Terraform/Telmate claims.

Intended outcome: the harness can run `just check` (Layers 0–2) on every
iteration to get a clean structured pass/fail it can self-correct against, never
mutating real infra; integration is gated behind `just integ` with credentials
scoped to a throwaway Proxmox pool that a runaway agent literally cannot escape.

## Task Description

Create `plugins/boss-dev/terraform-dev/` following this repo's plugin conventions
(mirroring `proxmox-infra` / the `ansible-dev` spec): a `plugin.json` manifest,
`README.md`, an async fmt/validate hook, a binary-selection wrapper, and two
model-invoked skills — `terraform-development` and `terraform-testing` — each with
`reference/`, `examples/`, `workflows/`, `anti-patterns/`, and PEP 723 `uv`-run
`tools/`. Author `ai_docs/terraform_tips_and_tricks.md` first as source material.
Retune `proxmox-infra` to a pve1-specific scope. Register `terraform-dev` in
`marketplace.json`, bump `proxmox-infra`, and pass `verify-structure.py` + repo
lint/markdown checks.

## Objective

A merge-ready `terraform-dev` plugin that: (1) guides OpenTofu/Terraform authoring
with `bpg/proxmox` + `kreuzwerker/docker`, small single-purpose modules, variable
validation, and the provisions-vs-configures boundary with an Ansible handoff;
(2) encodes the layered testing loop (Layer 0 static, Layer 1 plan-tests, Layer 2
`mock_provider` unit tests, Layer 3 disposable-infra apply, Terratest sparingly);
(3) ships `mise` + `justfile` + `.tftest.hcl`/`.tofutest.hcl` templates and a
disposable-infra safety model; (4) ships `uv`-based helper tools that emit
machine-readable pass/fail JSON for the harness, keystoned by a `test_loop.py`
orchestrator; (5) auto-runs `tofu fmt -check` + `validate` on `Stop`/`SubagentStop`.

## Problem Statement

The agent harness writes OpenTofu/Terraform but has no built-in, structured way to
validate it locally before applying to homelab resources — mistakes surface only
at apply time against real infra (slow, risky). There is also no curated guidance
encoding the provisions-vs-configures boundary, the `bpg`-over-`telmate` provider
choice, a deterministic mock-based unit layer, or a credential model that makes a
runaway agent physically unable to touch real resources.

## Solution Approach

Build a **two-skill** plugin mirroring `ansible-dev`: *knowledge* lives in
progressive-disclosure `reference/` files distilled from a new
`ai_docs/terraform_tips_and_tricks.md`; the *feedback loop* lives in `uv`-run
Python tools that return JSON. The headline deliverable is
`terraform-testing/tools/test_loop.py` — orchestrates Layer 0 → Layer 1 → Layer 2
(the `just check` inner loop) and returns one structured result with per-stage
pass/fail + remediation hints. The plugin ships **templates** (`.mise.toml`,
`justfile`, `.tftest.hcl`/`.tofutest.hcl`, module skeletons) that the agent
scaffolds into a *target* TF project — the plugin's own scripts operate on a
target directory. A `tofu`-first binary-selection wrapper (`terraform` fallback)
backs every script and the hook. The disposable-infra safety model (dedicated
`tf-test` Proxmox pool, `9xxx` VMID range, pool-scoped API token) is documented
and scaffolded so Layer 3 is the only mutating layer and it can only ever touch
throwaway infra.

## Relevant Files

Existing files to follow as patterns or to modify:

- `specs/ansible-dev-plugin.md` — **the sibling spec; mirror its shape exactly**
  (two skills, JSON-emitting `uv` tools, `test_loop` orchestrator, agent-harness
  focus, validation set). `terraform-dev` is its Terraform counterpart.
- `plugins/boss-homelab/proxmox-infra/skills/proxmox-infrastructure/SKILL.md` —
  gold-standard SKILL.md shape (frontmatter `name`+`description`, Trigger Phrases,
  Available Tools via `${CLAUDE_SKILL_DIR}` run with `uv run`, Core Capabilities,
  Quick Examples). **Also edited** to remove general-Terraform/Telmate claims.
- `plugins/boss-homelab/proxmox-infra/.claude-plugin/plugin.json` — manifest shape;
  **edited** to retune description/keywords (drop `terraform`/`opentofu`) + bump version.
- `.claude-plugin/marketplace.json` — add the `terraform-dev` entry (copy a
  `boss-dev` block, e.g. `python-dev`, retune); bump `proxmox-infra` entry.
- `templates/plugin-template/hooks/hooks.json` + `.claude-plugin/plugin.json` —
  hook wiring with `${CLAUDE_PLUGIN_ROOT}`; manifest skeleton.
- `scripts/verify-structure.py` — structure validator to run after scaffolding.
- `.claude/rules/plugin-structure.md`, `.claude/rules/skill-development.md`,
  `.claude/rules/python-scripts.md`, `.claude/rules/documentation.md` — binding
  standards. **Parser bug #12781: never use exclamation-mark+backtick or `@`
  patterns in SKILL.md code blocks — use `$ command` notation.**
- `ai_docs/ansible_tips_and_tricks.md` — format/depth reference for the new
  `terraform_tips_and_tricks.md` (the analogous source doc, which does not yet exist).

External references (already fetched): Terraform native tests
(`developer.hashicorp.com/terraform/language/tests`) and OpenTofu `tofu test`
(`opentofu.org/docs/cli/commands/test/`) — `mock_provider` and `override_*` are
OpenTofu 1.8+ (TF 1.7+); `.tofutest.hcl` takes precedence over `.tftest.hcl`.

### New Files

```text
ai_docs/terraform_tips_and_tricks.md          # Phase 0 source material

plugins/boss-dev/terraform-dev/
├── .claude-plugin/plugin.json
├── README.md
├── hooks/hooks.json                          # Stop + SubagentStop -> async fmt-check
├── scripts/
│   ├── tofu-or-terraform.sh                  # resolve OpenTofu first, fall back to terraform
│   └── fmt-check.sh                          # guarded: TF_BIN fmt -check + validate, scoped, never hard-fail
└── skills/
    ├── terraform-development/
    │   ├── SKILL.md
    │   ├── reference/
    │   │   ├── binary-selection.md           # OpenTofu default, terraform fallback, .tofutest precedence, CLI compat
    │   │   ├── providers.md                   # bpg/proxmox (VM+LXC, NOT telmate), kreuzwerker/docker (DOCKER_HOST=ssh://), pinning, auth
    │   │   ├── provisioning-vs-config.md      # "OpenTofu provisions, Ansible configures" boundary
    │   │   ├── modules.md                     # small single-purpose modules (lxc/vm/docker-stack); for_each/count; why they mock cleanly
    │   │   ├── variables-validation.md        # validation blocks, pre/postconditions (cheap Layer 0 checks)
    │   │   ├── state-backends.md              # separate dev/iteration backend from real; per-env state isolation
    │   │   └── ansible-handoff.md             # cloud-init user-data + generate Ansible inventory from TF outputs; cross-ref ansible-dev
    │   ├── anti-patterns/common-mistakes.md   # null_resource/remote-exec, telmate, configuring existing hosts, monolithic modules
    │   ├── examples/
    │   │   ├── module-lxc/                     # bpg proxmox_virtual_environment_container module
    │   │   ├── module-docker-stack/            # kreuzwerker/docker over remote daemon
    │   │   └── ansible-handoff/                # cloud-init + inventory-generation snippet
    │   ├── workflows/new-module.md
    │   └── tools/
    │       ├── validate_static.py             # Layer 0: fmt -check + validate + tflint + trivy config -> JSON
    │       └── module_scaffold.py             # generate lxc/vm/docker-stack skeleton (+ vars/validation/outputs/.tftest stub)
    └── terraform-testing/
        ├── SKILL.md
        ├── reference/
        │   ├── testing-layers.md              # the 0-3 layered loop, fast->slow, what runs where
        │   ├── native-tests.md                # .tftest.hcl/.tofutest.hcl run blocks, plan vs apply, assert, expect_failures, state_key
        │   ├── mocking.md                     # mock_provider (1.8+), override_resource/data/module — deterministic Layer 2
        │   ├── static-analysis.md             # fmt/validate, tflint, trivy config, checkov via uvx
        │   ├── disposable-infra.md            # tf-test pool, 9xxx VMID range, pool-scoped API token (primary rail), LXC>VM, cloud-init golden template
        │   ├── terratest.md                   # sparingly; ApplyAndIdempotent, HTTP/SSH; Go via mise; gated outer loop only
        │   └── agent-harness-loop.md          # just check (inner) vs just integ (gated outer); per-test state isolation; structured pass/fail
        ├── anti-patterns/testing-mistakes.md  # applying against real infra, no state isolation, mocking everything, terratest in fast loop
        ├── examples/
        │   ├── mise.toml                       # pins opentofu, terraform, tflint, trivy, go
        │   ├── justfile                        # just check (Layers 0-2) + just integ (Layer 3, gated)
        │   ├── tftest-plan/                     # Layer 1: command = plan native test
        │   ├── tftest-mock/                     # Layer 2: mock_provider .tofutest.hcl (zero API calls)
        │   └── terratest/                       # one Go test: ApplyAndIdempotent + SSH/HTTP check
        ├── workflows/
        │   ├── dev-feedback-loop.md             # the tight `just check` loop the harness follows
        │   ├── disposable-infra-setup.md        # create pool + scoped token + VMID range
        │   └── pre-apply-checklist.md
        └── tools/
            ├── tftest_run.py                    # run `TF_BIN test -json`, parse runs/assertions -> JSON
            └── test_loop.py                     # KEYSTONE: Layer 0 -> 1 -> 2 (== just check); single structured result + remediation hints
```

## Implementation Phases

### Phase 0: Source material

Author `ai_docs/terraform_tips_and_tricks.md` (mirroring the depth/format of
`ansible_tips_and_tricks.md`). It is the single source the skill `reference/`
files are distilled from. Cover: OpenTofu-vs-Terraform + binary selection;
providers (`bpg/proxmox`, `kreuzwerker/docker` incl. `DOCKER_HOST=ssh://`);
provisions-vs-configures boundary + Ansible handoff (cloud-init, generated
inventory) and the `null_resource`/`remote-exec` anti-pattern; small
single-purpose modules; the layered testing loop 0–3; native tests + `mock_provider`
+ `override_*` (1.8+) + `.tofutest.hcl` precedence; disposable-infra safety model
(pool, `9xxx` VMID range, scoped token, LXC>VM, cloud-init golden template);
`mise` toolchain pinning + `uv`/`uvx` for `checkov`; the `just check` / `just integ`
loop; state isolation / separate dev backend; Terratest used sparingly.

### Phase 1: Foundation

Scaffold `plugins/boss-dev/terraform-dev/` from `templates/plugin-template`. Write
`plugin.json` and the binary-selection wrapper + fmt-check hook script; wire
`hooks/hooks.json`. Register in `marketplace.json`. Retune `proxmox-infra`
(description, SKILL.md, keywords) to pve1-specific scope + bump its version. Get
`verify-structure.py` passing with empty-but-valid skills.

### Phase 2: Core Implementation

Author both `SKILL.md` files and all `reference/` content (distilled from
Phase 0), then implement the PEP 723 tools — JSON output first, with `test_loop.py`
as the keystone (`validate_static.py` and `tftest_run.py` are its stages).

### Phase 3: Integration & Polish

Add `examples/` (incl. `mise.toml`, `justfile`, plan/mock `.tftest`/`.tofutest`
files, one Terratest Go example), `workflows/`, `anti-patterns/`; write the
`README.md`; add importlib smoke tests for the tools; run full repo validation and
fix all findings; run `version-bump-reviewer` on both plugins.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Author the tips source doc (Phase 0)

- Create `ai_docs/terraform_tips_and_tricks.md` covering every topic listed in
  Phase 0. Ground provider/test claims in the HashiCorp + OpenTofu docs.

### 2. Scaffold plugin skeleton

- Create `plugins/boss-dev/terraform-dev/` with `.claude-plugin/`, `hooks/`,
  `scripts/`, and
  `skills/terraform-development|terraform-testing/{reference,examples,workflows,anti-patterns,tools}/`.
- Write `plugin.json`: name `terraform-dev`, `displayName` "Terraform Dev",
  version `0.1.0`, MIT, author/homepage/repository matching `python-dev`,
  keywords `[terraform, opentofu, tofu, iac, mock-provider, tftest, tflint, trivy,
  terratest, mise, bpg-proxmox, docker, testing, agent-harness]`.

### 3. Binary-selection wrapper + fmt hook

- `scripts/tofu-or-terraform.sh`: resolve `tofu` first, fall back to `terraform`;
  export/echo the chosen `TF_BIN`; no-op cleanly when neither is present.
- `scripts/fmt-check.sh`: source the wrapper; run `"$TF_BIN" fmt -check -recursive`
  + `"$TF_BIN" validate`; scope to dirs containing `*.tf`; never hard-fail (`|| true`);
  non-mutating (no auto-rewrite).
- `hooks/hooks.json`: `Stop` and `SubagentStop` each run
  `bash "${CLAUDE_PLUGIN_ROOT}/scripts/fmt-check.sh"` with `"async": true`.

### 4. Register in marketplace + retune proxmox-infra

- Add a `terraform-dev` entry to `.claude-plugin/marketplace.json` (category
  `boss-dev`, `source ./plugins/boss-dev/terraform-dev`, matching
  description/keywords/author).
- Edit `proxmox-infra` `plugin.json` + `marketplace.json` entry + its `SKILL.md`:
  remove general Terraform/OpenTofu/Telmate claims and the
  "Deploy VMs using OpenTofu/Terraform" trigger; reframe as **pve1 homelab
  host operations** (proxmoxer, cluster/ceph/storage, Ansible
  `community.general.proxmox`); add a cross-reference: "for general
  Terraform/OpenTofu authoring + testing, use `terraform-dev`." Bump its version.

### 5. Write terraform-development SKILL.md + reference content

- Frontmatter `name: terraform-development` + concrete `description` (mentions
  OpenTofu/Terraform authoring, bpg/proxmox + kreuzwerker/docker, modules,
  provisions-vs-configures). Sections: Trigger Phrases, Available Tools (via
  `${CLAUDE_SKILL_DIR}`, `uv run`), Core Capabilities, Quick Examples, "For
  Details" index linking every `reference/`/`examples/`/`workflows/`/`anti-patterns/`
  file. Use `$ command` notation only.
- `reference/`: `binary-selection.md`, `providers.md`, `provisioning-vs-config.md`,
  `modules.md`, `variables-validation.md`, `state-backends.md`, `ansible-handoff.md`.

### 6. Implement terraform-development tools (PEP 723, JSON)

- `validate_static.py` — Layer 0 aggregator over a `--dir`: `TF_BIN fmt -check`,
  `TF_BIN validate`, `tflint`, `trivy config`; emit `{ok, stages[], findings[]}`.
- `module_scaffold.py` — `--kind {lxc,vm,docker-stack} --name` generates a
  single-purpose module skeleton (`main.tf`, `variables.tf` with validation,
  `outputs.tf`, a `tests/*.tftest.hcl` plan stub).
- Each: `from __future__ import annotations`, full types, `argparse` `--help`,
  `--json` with top-level `ok`, side-effect-free import via `__main__` guard,
  shell out to CLIs (don't import them).

### 7. Write terraform-testing SKILL.md + reference content

- SKILL.md mirroring step 5, oriented to the layered loop.
- `reference/`: `testing-layers.md`, `native-tests.md`, `mocking.md`,
  `static-analysis.md`, `disposable-infra.md`, `terratest.md`,
  `agent-harness-loop.md`. Recommend the hermetic `just check` (Layers 0–2) as the
  agent's iterate target; document the pool-scoped-token safety rail as primary.

### 8. Implement terraform-testing tools (PEP 723, JSON)

- `tftest_run.py` — run `TF_BIN test -json` for a `--dir`/`--filter`; parse run
  blocks + assertion outcomes into `{ok, runs[], failures[]}`.
- `test_loop.py` — KEYSTONE: orchestrate Layer 0 (`validate_static`) → Layer 1
  (plan `.tftest` via `tftest_run`) → Layer 2 (mock `.tofutest`); emit one
  structured result with per-stage pass/fail + a short remediation hint per
  failure. This is the `just check` programmatic equivalent the harness calls.

### 9. Add examples, workflows, anti-patterns, README

- Examples: `module-lxc/`, `module-docker-stack/`, `ansible-handoff/`;
  `mise.toml` (opentofu, terraform, tflint, trivy, go), `justfile`
  (`check` = Layers 0–2 hermetic, `integ` = Layer 3 gated/approval),
  `tftest-plan/`, `tftest-mock/`, one `terratest/` Go test (ApplyAndIdempotent +
  SSH/HTTP). NOTE: examples are templates the agent scaffolds into a *target* TF
  project, not run from the plugin repo.
- Workflows: `new-module.md`, `dev-feedback-loop.md`, `disposable-infra-setup.md`,
  `pre-apply-checklist.md`. Anti-patterns for both skills.
- `README.md` (required): features, requirements (`mise` toolchain; `uvx checkov`;
  Go for Terratest), skills list, hook behavior, the `just check`/`just integ`
  loop, the disposable-infra safety model, install.

### 10. Add smoke tests

- In `tests/`, load each new PEP 723 tool via
  `importlib.util.spec_from_file_location` (repo pattern) to assert importability
  and a callable entry point. No trivial tests beyond this.

### 11. Validate everything

- Run `scripts/verify-structure.py`, `make lint`, `make markdown-lint`,
  `make link-check`, `make test`; fix every finding until clean.
- Run the `version-bump-reviewer` skill against `terraform-dev` (initial publish)
  and `proxmox-infra` (retune bump) to confirm version artifacts + marketplace
  parity.

## Testing Strategy

- **Structure**: `scripts/verify-structure.py` passes (manifest schema, SKILL.md
  frontmatter, component placement, marketplace parity for both plugins).
- **Python**: `make lint` (ruff + basedpyright) clean on new tools; `make test`
  runs importlib smoke tests (PEP 723 import without side effects via `__main__`).
- **Markdown**: `make markdown-lint` (rumdl) + `make link-check` (lychee) clean.
- **Tool behavior (manual)**: against a throwaway sample module —
  `uv run .../terraform-development/tools/validate_static.py --dir <m> --json`,
  `module_scaffold.py --kind lxc --name foo`, `tftest_run.py`, and `test_loop.py`
  each emit valid JSON with a correct top-level `ok` for passing and
  intentionally-broken input. The mock `.tofutest.hcl` example must run with
  **zero API calls** under `TF_BIN test`.
- **Hook**: `scripts/fmt-check.sh` no-ops gracefully when neither `tofu` nor
  `terraform` is present; reports fmt/validate status when present; never blocks.
- **Binary selection**: `tofu-or-terraform.sh` picks `tofu` when present, falls
  back to `terraform`, exits cleanly when neither exists.

## Acceptance Criteria

- `plugins/boss-dev/terraform-dev/` exists with manifest, README, hook, wrapper,
  and two skills, each with `reference/`, `examples/`, `workflows/`,
  `anti-patterns/`, `tools/`.
- `terraform-dev` is registered in `marketplace.json`; `proxmox-infra` is retuned
  to pve1-specific scope (no general Terraform/Telmate claims) with a version bump,
  and both plugins keep `plugin.json`↔`marketplace.json` version parity.
- All helper tools are PEP 723, run via `uv`, typed, emit structured JSON with a
  top-level `ok`; `test_loop.py` orchestrates Layers 0–2 with per-stage results +
  remediation hints.
- The plugin defaults to OpenTofu (`terraform` fallback) everywhere via the wrapper.
- Skills encode: `bpg/proxmox` + `kreuzwerker/docker` (NOT telmate); the
  provisions-vs-configures boundary + Ansible handoff; `null_resource`/`remote-exec`
  as anti-pattern; small single-purpose modules; the layered loop 0–3 with
  `mock_provider` Layer 2; the disposable-infra safety model (pool + `9xxx` range +
  pool-scoped token); `just check` (hermetic inner) vs `just integ` (gated outer).
- Terratest is documented + one runnable Go example, with the Go toolchain pinned
  in `mise.toml` and kept out of the fast loop (no tool wrapper).
- No exclamation-mark+backtick / `@` patterns in any SKILL.md (parser-bug safe).
- `verify-structure.py`, `make lint`, `make markdown-lint`, `make link-check`,
  `make test` all pass.

## Validation Commands

- `uv run scripts/verify-structure.py` — validate marketplace + plugin structure.
- `make lint` — ruff + basedpyright on new tools.
- `make test` — importlib smoke tests for the new PEP 723 scripts.
- `make markdown-lint` — rumdl on new markdown.
- `make link-check` — lychee on new markdown links.
- `uv run plugins/boss-dev/terraform-dev/skills/terraform-testing/tools/test_loop.py --help`
  — confirm the keystone tool loads and exposes its interface.
- `bash plugins/boss-dev/terraform-dev/scripts/tofu-or-terraform.sh` — confirm
  binary resolution (tofu first, terraform fallback).

## Notes

- **Category**: `boss-dev` (confirmed) — general TF/OpenTofu development tool,
  sibling to `python-dev`. `proxmox-infra` + `ansible-dev` remain `boss-homelab`.
- **proxmox-infra boundary** (confirmed): `terraform-dev` is the general TF plugin;
  `proxmox-infra` is for operating the user's specific pve1 homelab host. Each
  cross-references the other rather than overlapping.
- **Toolchain** (confirmed): `mise` pins `opentofu` (primary), `terraform`,
  `tflint`, `trivy`, and `go` (Terratest); `uv`/`uvx` runs Python tooling
  (`checkov`). Plugin scripts are PEP 723 `uv run --script` with pinned inline deps
  (e.g. `["rich"]`); they shell out to CLIs rather than importing them. `mise.toml`
  + `justfile` ship as **templates** scaffolded into the target TF project.
- **Terratest** (confirmed): doc + one minimal Go example, no fast-loop tool
  wrapper.
- **Agent-harness focus**: every tool's JSON includes per-stage pass/fail, file +
  line of failures where available, and a short remediation hint — the core
  differentiator from the upstream `han` terraform plugin (content + format hook
  + LSP only; no testing tooling, Terraform-only, no OpenTofu).
- **Optional follow-up (not in scope)**: a `terraform-ls` LSP server entry
  (`lspServers` in `plugin.json`) like `han` ships — note it for later.
