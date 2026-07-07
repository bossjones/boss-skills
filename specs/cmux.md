# Plan: Incorporate the cmux skill + generalized team orchestration into agent-harness

> **Status:** approved spec, ready to implement in a fresh session.
> **Deliverable:** new skills + commands under `plugins/boss-dev/agent-harness`.

## Context

`/Users/bossjones/dev/disler-aka-indydevdan/learning-cmux-with-agents` is IndyDevDan's teaching
repo showing a single orchestrator agent driving a **fleet** of terminal agents through
[cmux](https://cmux.com) — a native macOS terminal (Homebrew cask `manaflow-ai/cmux`) that
exposes a CLI + Unix socket so every window/workspace/pane/surface is an addressable,
scriptable object. We want that capability inside the **agent-harness** plugin
(`plugins/boss-dev/agent-harness`), which already hosts our subagent/command/hook/skill
tooling.

Two distinct things live in the source repo:

1. **A clean, self-contained `cmux` driver skill** (`.claude/skills/cmux/SKILL.md`) — pure
   natural-language cmux control (open/inspect/prompt/read/tear-down surfaces + a
   push-notification wait loop). No bundled scripts, no repo coupling. **Ports nearly verbatim.**
2. **An opinionated 5-agent "full-stack team" feature** (`spawn-fs-team.md`,
   `cmux-did-spawn.md`, `cmux-fresh.md`, `scripts/spawn_fast.py`, `cmux/fs-team.layout.json`,
   `.claude/agents/{lead,plan,build-be,build-fe,test}.md`) — **hardcoded** to the repo's
   `apps/flotion` demo (a Vue3/FastAPI Notion clone), specific OpenRouter models
   (`z-ai/glm-5.2`, `minimax/minimax-m3`), and a `FLOTION-DONE:` completion sentinel.

**Decisions (confirmed with the user):**
- **Scope = Skill + generalized team.** Port both, but strip flotion/hardcoded models so the
  team-spawn is reusable — repo, app, roles, models, and sentinel become config with sane
  defaults.
- **References = vendor core.** Copy the 4 agent-facing `cmux/references/*.md` (tiny, ~126 lines
  total) into `skills/cmux/references/`; point to `npx skills add manaflow-ai/cmux` for the
  deeper 20-skill vendor set rather than vendoring all of it.
- **Skip `context_bar.py`.** agent-harness already ships `status_line.py … v10`, and v10 renders
  a richer context-window bar + cost. The generic cmux bar is redundant.

**Completeness audit (re-verified against source before implementing):**
- The 4 vendored references are **self-contained** — no dangling links to scripts/assets we'd
  omit. Safe to copy verbatim.
- `ai_docs/cmux-skills/cmux/agents/openai.yaml` is **intentionally not vendored** — it's a
  Codex/OpenAI harness *interface manifest* (display_name/short_description/default_prompt),
  irrelevant to Claude Code, which reads SKILL.md frontmatter.
- **The two `cmux` SKILL.md files are complementary, not duplicates.** We port the *orchestration*
  one (`.claude/skills/cmux/SKILL.md`). The vendor *topology* one (`ai_docs/cmux-skills/cmux/SKILL.md`,
  "cmux Core Control") carries two things the ported skill otherwise **lacks**, grafted into the
  ported SKILL.md rather than left out: (1) **settings/reload discipline** — `cmux docs settings`,
  back up `cmux.json` before editing, `cmux reload-config` (reloads both cmux.json + Ghostty
  config), and the cmux.json-vs-Ghostty split; load-bearing because our Prerequisites already
  instruct editing `cmux.json` for `socketControlMode`. (2) **topology-routing verbs** —
  `move-surface`, `reorder-surface`, `split-off`, `surface-health`, `--id-format` — already
  covered by the 4 references, surfaced via a Deep-Dive References table.

**Outcome:** agent-harness gains an `agent-harness:cmux` skill (drive cmux from natural language)
and an `agent-harness:cmux-team` skill + slash commands (`/cmux-spawn-team`, `/cmux-did-spawn`,
`/cmux-fresh`) that boot and orient a configurable multi-agent terminal team — with no flotion
baggage.

## Objective

Add to `plugins/boss-dev/agent-harness`:
- `skills/cmux/` — the ported driver skill + vendored references.
- `skills/cmux-team/` — a generalized, config-driven team-spawn skill (SKILL.md + PEP723
  `spawn_team.py` + tests + role/layout/config assets).
- `commands/cmux-fresh.md`, `commands/cmux-spawn-team.md`, `commands/cmux-did-spawn.md` — thin
  slash-command entry points.
- Docs + version bump (0.20.0 → **0.21.0**, minor) across `plugin.json`, `marketplace.json`,
  `CHANGELOG.md`, and the plugin's `docs/`.

All flotion/model hardcoding removed; the team feature works with zero config (bundled defaults)
and is fully overridable.

## Problem Statement

The valuable, reusable artifact — driving cmux from natural language — is entangled in the source
repo with a demo-specific team feature. A naive copy would drag `apps/flotion`, GLM/Minimax model
IDs, and a `FLOTION-DONE:` protocol into agent-harness, making the team feature useless outside
that one demo and confusing to maintainers. We need a faithful port of the generic skill plus a
**generalized** team feature whose specifics are data, not code.

## Solution Approach

- **Driver skill:** near-verbatim port. Only additions: house-style frontmatter
  (`allowed-tools: Bash`), a **Prerequisites** section (Homebrew cask install, `cmux hooks setup`,
  `automation.socketControlMode: allowAll`, `/usr/local/bin/cmux` symlink, macOS 14+), a
  `references/` pointer + vendored files, and the `npx skills add manaflow-ai/cmux` note.
- **Team feature:** invert the hardcoding into a **team-config JSON** consumed by a generalized
  `spawn_team.py`. Config declares `roles[]` (name + model + role-prompt file + optional
  completion sentinel), `cwd`/repo, and the layout. The script generates the cmux
  `--layout` JSON from the config (replacing the static `fs-team.layout.json` template
  interpolation) so any role set / model blend / app works. Bundled default config = a generic
  5-role full-stack team (lead + plan + build-be + build-fe + test) with **placeholder** models
  and a generic `TASK-DONE:` sentinel. Role prompt templates are stack-agnostic and parameterized
  on app path + stack description.
- **Commands** stay thin: `cmux-fresh` is standalone (generic macOS session reset);
  `cmux-spawn-team` and `cmux-did-spawn` reference the `cmux-team` skill's script/assets via
  `${CLAUDE_PLUGIN_ROOT}`.

## Relevant Files

### Source (read-only, to copy/adapt from)
- `…/learning-cmux-with-agents/.claude/skills/cmux/SKILL.md` — the driver skill (port ~verbatim).
- `…/ai_docs/cmux-skills/cmux/references/{handles-and-identify,panes-surfaces,windows-workspaces,trigger-flash-and-health}.md` — the 4 tiny references to vendor.
- `…/scripts/spawn_fast.py` — fast-path spawner (generalize: lift `MODELS`, `ROLES`, `REPO`, layout path, `FLOTION` strings into config/flags; keep `slugify`/`ensure_cmux_running`/`find_or_create_window`/window-reuse logic).
- `…/cmux/fs-team.layout.json` — layout template (replace static interpolation with config-driven generation, or keep a generic placeholder template).
- `…/.claude/commands/{spawn-fs-team,cmux-did-spawn,cmux-fresh}.md` — the 3 commands (generalize first two, port third as-is).
- `…/.claude/agents/{lead,plan,build-be,build-fe,test}.md` — role prompts (generalize: remove flotion/apps/flotion/stack hardcoding; `FLOTION-DONE:` → configurable sentinel; reconcile the notification-match inconsistency — `lead.md` greps `surface_ref` but the driver SKILL.md says match on `workspace_id` since `surface_id` is often null — standardize on the SKILL.md guidance).

### Target house-style references (match these patterns)
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — manifest; `"skills": "./skills/"` (commands/agents auto-discovered); `version` lives here.
- `plugins/boss-dev/agent-harness/skills/unicode-hygiene/SKILL.md` — frontmatter style (`allowed-tools` YAML list; no per-skill version).
- `plugins/boss-dev/agent-harness/skills/release-notes-generator/SKILL.md` — inline `allowed-tools: Bash` + `assets/` + `references/` layout.
- `plugins/boss-dev/agent-harness/skills/worktree-doctor/scripts/{worktree_doctor.py,tests/conftest.py,tests/test_worktree_doctor.py}` — PEP723 script + `scripts/tests/` `sys.path`-shim test pattern.
- `plugins/boss-dev/agent-harness/commands/validate-unicode-hygiene.md` — command frontmatter style (`description` + `argument-hint` + `allowed-tools`).
- `.claude-plugin/marketplace.json` — agent-harness entry `version` (parity with plugin.json).
- `CHANGELOG.md` — Keep-a-Changelog `### Added` format.
- `.claude/skills/version-bump-reviewer/SKILL.md` — governs the bump (plugin.json + marketplace.json parity; new skill ⇒ minor).

### New Files
```
plugins/boss-dev/agent-harness/
├── skills/cmux/
│   ├── SKILL.md                              # ported driver + Prerequisites + references pointer
│   └── references/
│       ├── handles-and-identify.md           # vendored
│       ├── panes-surfaces.md                 # vendored
│       ├── windows-workspaces.md             # vendored
│       └── trigger-flash-and-health.md       # vendored
├── skills/cmux-team/
│   ├── SKILL.md                              # generalized spawn+orient+drive recipe
│   ├── scripts/
│   │   ├── spawn_team.py                     # generalized spawn_fast.py (PEP723, config-driven, --dry-run)
│   │   └── tests/
│   │       ├── conftest.py                    # sys.path shim
│   │       └── test_spawn_team.py             # pure-helper tests (slugify, config load, layout build)
│   └── assets/
│       ├── team-config.example.json          # roles/models/cwd/sentinel example (documented)
│       ├── team-layout.template.json         # generic layout template (or generated in-script)
│       └── roles/{lead,plan,build-be,build-fe,test}.md   # generalized role prompts
├── commands/
│   ├── cmux-fresh.md                         # ported ~as-is (generic macOS session reset)
│   ├── cmux-spawn-team.md                     # wrapper → cmux-team skill / spawn_team.py
│   └── cmux-did-spawn.md                      # generalized orient command
```
(Skip `prime.md` — collides with agent-harness's existing `commands/prime.md`. Skip `context_bar.py`. `just` recipes are NOT ported — `/cmux-spawn-team` + `spawn_team.py` replace them.)

## Implementation Phases

### Phase 1: Foundation — the driver skill (independently useful)
Port `skills/cmux/` + vendor references. This alone delivers "drive cmux from natural language"
and has zero coupling, so it can ship/verify first.

### Phase 2: Core — generalized team feature
Build `skills/cmux-team/` (config-driven `spawn_team.py` + generalized role/layout/config assets)
and the 3 commands. This is where all flotion/model hardcoding is inverted into config.

### Phase 3: Integration & Polish
Docs, version bump, CHANGELOG, lint/test, unicode-hygiene scan, and a documented (macOS-only)
end-to-end smoke path + a CI-safe `--dry-run`.

## Step by Step Tasks

### 1. Create the driver skill `skills/cmux/SKILL.md`
- Copy the source SKILL.md body verbatim (it is already cmux-generic — no flotion).
- Frontmatter: keep `name: cmux`, keep the trigger-rich `description` and `argument-hint`; **add** `allowed-tools: Bash` (inline scalar, matching `release-notes-generator`) — the skill fundamentally shells out to `cmux`/`claude`/`codex`/`pi`/`jq`.
- Add a **Prerequisites** section: `brew tap manaflow-ai/cmux && brew install --cask cmux`; optional `/usr/local/bin/cmux` symlink; `cmux hooks setup` (for pi/codex/gemini turn-stop events; Claude Code emits out of the box); `automation.socketControlMode: allowAll` in `~/.config/cmux/cmux.json` for an orchestrator outside cmux; macOS 14+; validated against cmux `0.64.17`.
- Add a **References** section linking the 4 vendored files + `npx skills add manaflow-ai/cmux -g -y` for the full vendor skill set.
- Note in the skill (or docs) the potential name overlap with the globally-installed vendor `cmux` skill — harmless because agent-harness namespaces as `agent-harness:cmux`.

### 2. Vendor the 4 references into `skills/cmux/references/`
- Copy the 4 files from `ai_docs/cmux-skills/cmux/references/` unchanged.

### 3. Generalize the spawner → `skills/cmux-team/scripts/spawn_team.py`
- Start from `spawn_fast.py`. Keep: `slugify`, `sh`/`cmux`/`cmux_json`, `ensure_cmux_running`, `find_or_create_window` (window-reuse + stable-UUID logic), `write_spawn_file`, `exec_orchestrator`.
- **Remove hardcoding:** replace module-level `MODELS`/`ROLES`/`REPO`/`LAYOUT_FILE` and all `Flotion` strings with values loaded from a **team-config JSON**. Resolve config in order: `--config <path>` → `./.cmux/team.json` → bundled `assets/team-config.example.json` default.
- Config schema (documented in the example): `{ "cwd": "<repo>", "env_file": ".env", "completion_sentinel": "TASK-DONE", "orchestrator": {"cc": {...}, "pi": {"model": "..."}}, "roles": [ {"name":"lead","model":"<PLACEHOLDER>","prompt":"roles/lead.md","kickoff":"..."}, ... ] }`.
- **Generate the cmux `--layout` JSON from the config** (lead left-half + remaining roles in a grid) instead of interpolating a static flotion template. Role prompt paths resolve against the skill's `assets/roles/` unless the config overrides with an absolute/user path.
- Add `--dry-run`: print the resolved config + generated layout + the cmux commands it *would* run, and exit 0 without touching cmux (CI-safe, and the basis for tests).
- PEP723 header house style: `#!/usr/bin/env -S uv run --script`, `requires-python = ">=3.13"`, `dependencies = []` (stdlib only). Keep IO side-effect-free helpers pure for testing.
- CLI: `spawn_team.py <cc|pi> <feature-slug> [--config PATH] [--cwd DIR] [--orch-pi-model MODEL] [--dry-run]`.

### 4. Generalize the layout + role assets
- **No `team-layout.template.json` asset.** `spawn_team.py` generates the cmux `--layout` from the team-config at runtime — fewer moving parts than maintaining a static template with placeholder tokens (`__CWD__`, per-role `__MODEL__`/`__PROMPT__`/`__NAME__`). The generalized form of `fs-team.layout.json` lives only as the script's generation logic, not as a checked-in template file.
- `assets/roles/{lead,plan,build-be,build-fe,test}.md`: copy the source role prompts, then strip flotion — parameterize app path + stack (drive from config, e.g. "app: `<APP_PATH>`", "stack: `<STACK>`"); replace `FLOTION-DONE:` with the configurable `<SENTINEL>` (default `TASK-DONE:`); reconcile lead's notification wait to match on `workspace_id` per the driver SKILL.md (not `surface_ref`). Keep the generic patterns: one-line `send` + `send-key enter`, completion contract, push-over-poll, lane discipline.
- `assets/team-config.example.json`: a fully-documented example wiring the 5 roles with **placeholder** model IDs (e.g. `"<your-orchestrator-model>"`) and `TASK-DONE` sentinel.

### 5. Create the team skill `skills/cmux-team/SKILL.md`
- Merge the recipe content of `spawn-fs-team.md` + `cmux-did-spawn.md`, generalized: how to spawn a team (via `spawn_team.py` or by driving cmux verbs directly), how to orient onto an existing team by stable window UUID + workspace name, and how to drive the lead. Reference the driver skill (`agent-harness:cmux`) for the verb-level details rather than duplicating.
- Frontmatter house style: `name: cmux-team`, trigger-rich `description`, `allowed-tools: Bash`.

### 6. Add the 3 commands
- `commands/cmux-fresh.md`: port ~verbatim (already generic — clears `~/Library/Application Support/cmux/session-com.cmuxterm.app*.json`). Keep `allowed-tools: Bash`; drop `model: opus` or keep per house preference (agent-harness commands generally omit `model`).
- `commands/cmux-spawn-team.md`: generalized `spawn-fs-team.md` — thin wrapper that runs `uv run "${CLAUDE_PLUGIN_ROOT}"/skills/cmux-team/scripts/spawn_team.py` (or points at the `cmux-team` skill recipe). `argument-hint: [team-name] [feature description...] [--config PATH]`. Remove all flotion/model text; defer specifics to config.
- `commands/cmux-did-spawn.md`: generalized orient command — remove flotion, use `<SENTINEL>`, reference the `cmux-team` skill.

### 7. Docs + version bump
- **Version bump — don't hand-edit.** Per `CONTRIBUTING.md`, let the `version-bump-reviewer` skill (auto-triggered by the plugin-component hook on commit) bump `plugin.json` `version` **0.20.0 → 0.21.0** and the matching `marketplace.json` agent-harness entry to `0.21.0` (parity; new skills+commands ⇒ minor). Do not set these versions by hand.
- Add `CHANGELOG.md` `### Added` lines under `## [Unreleased]` (phrasing `… (v0.21.0) by @bossjones`): the `cmux` driver skill, the `cmux-team` skill, and the 3 commands.
- Update the plugin's `docs/skills.md`, `docs/commands.md` (and README skill/command lists) to include the new entries, matching existing formatting.

### 8. Validate (final step)
- Run the PEP723 tests, `make lint`, `make test`, and a unicode-hygiene scan on the new SKILL.md/command/JSON files. Confirm `spawn_team.py --dry-run` produces a correct layout with placeholder models and no flotion strings. See **Validation Commands**.

## Testing Strategy
- **Unit (CI-safe, no macOS/cmux needed):** `scripts/tests/test_spawn_team.py` using the `worktree-doctor` `conftest.py` `sys.path`-shim pattern. Cover the pure helpers: `slugify` (spaces/punctuation → dash-case), team-config loading + default fallback, and layout generation from a config (assert role count, models threaded, cwd substituted, **no `flotion`/`FLOTION-DONE` substrings**). Exercise `--dry-run` via subprocess (`sys.executable`) asserting exit 0 + expected stdout — the CLAUDE.md-sanctioned exception for stdlib PEP723 CLI scripts.
- **Static:** unicode-hygiene scan of new `SKILL.md`/command/JSON. `make lint` (ruff + basedpyright) on the new script. Grep the whole new footprint for `flotion`/`FLOTION`/`glm-5.2`/`minimax` to prove generalization.
- **Manual e2e (macOS + cmux only, documented, not in CI):** install cmux, `cmux --help`, then `/cmux-spawn-team demo "add a health endpoint"` with a minimal config; confirm a workspace boots, `/cmux-did-spawn` orients, and `/cmux-fresh` resets the session. Note in docs that CI cannot run this (macOS app dependency) — the `--dry-run` path is the automated proxy.

## Acceptance Criteria
- `skills/cmux/SKILL.md` exists with house-style frontmatter (`allowed-tools`), a Prerequisites section, and `references/` with the 4 vendored files; triggers as `agent-harness:cmux`.
- `skills/cmux-team/` exists with a config-driven `spawn_team.py` (+ passing tests), generalized role/layout/config assets, and a SKILL.md; `--dry-run` works with zero config.
- `commands/cmux-fresh.md`, `commands/cmux-spawn-team.md`, `commands/cmux-did-spawn.md` are discoverable as `agent-harness:*`.
- **No `flotion`/`FLOTION-DONE`/hardcoded `glm-5.2`/`minimax` strings** anywhere in the new files (models are placeholders/config).
- `context_bar.py` and `prime.md` are NOT added.
- `plugin.json` and `marketplace.json` both at `0.21.0` — produced by the `version-bump-reviewer` skill/hook on commit, not hand-edited; `CHANGELOG.md` updated; plugin docs list the new skills/commands.
- `make lint` and `make test` pass; unicode-hygiene scan clean.

## Validation Commands
- `uv run pytest -s plugins/boss-dev/agent-harness/skills/cmux-team/scripts/tests/` — team-spawn helper + dry-run tests pass.
- `uv run plugins/boss-dev/agent-harness/skills/cmux-team/scripts/spawn_team.py cc demo --dry-run` — prints resolved config + generated layout, exit 0, no cmux contact.
- `make lint` — ruff + basedpyright clean on the new script.
- `make test` — full suite green.
- `uv run scripts/validate-unicode-hygiene.py plugins/boss-dev/agent-harness/skills/cmux plugins/boss-dev/agent-harness/skills/cmux-team plugins/boss-dev/agent-harness/commands/cmux-*.md` — no hidden/spoofed Unicode.
- `grep -rniE 'flotion|glm-5\.2|minimax' plugins/boss-dev/agent-harness/skills/cmux-team plugins/boss-dev/agent-harness/commands/cmux-*.md` — returns nothing (generalization proof).
- `python -c "import json,glob; [json.load(open(f)) for f in glob.glob('plugins/boss-dev/agent-harness/skills/cmux-team/assets/*.json')]"` — asset JSON is valid.

## Notes
- **Platform:** cmux is macOS-only (Homebrew cask). The skills trigger anywhere but only function on macOS with cmux installed; document prereqs and keep automated tests host-independent via `--dry-run`.
- **No new Python deps** — everything is stdlib (`uv add` not needed). PEP723 scripts pin `requires-python = ">=3.13"` per house style.
- **Version-bump-reviewer** (`.claude/skills/version-bump-reviewer`) will validate the plugin.json ↔ marketplace.json parity + minor classification on commit.
- **Fidelity vs. reuse:** we intentionally keep the 5-role full-stack team as the *default* shape (faithful to the source) while making roles/models/app/sentinel data — so the demo still works out of the box and any other team is just a different config.
- **`.team/` convention** (roster/backlog/role notes shared memory) is kept generic and documented; it is the team's scratch dir, path configurable.
