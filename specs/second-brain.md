# Spec: Port the "second brain" (setup-second-brain) feature into boss-skills

## Context

The "second brain" feature was built on the `feature-second-brain` branch of
`~/dev/adobe-aifoundations/aif-skills` (two commits: `9912e7f` obsidian-wiki
docs/config + `5f27181` the `setup-second-brain` skill). boss-skills already
mirrors aif-skills' `agent-harness` plugin and has an established backport lane
(`specs/backport-agent-harness-*.md`, `specs/port-skills-to-agent-harness.md`).
This spec captures exactly what changed in aif-skills and ports it into
boss-skills, with **one deliberate difference**: the default vault path changes
from `~/Documents/obsidian/work.vault` (Adobe/work context) to
`~/Documents/obsidian/personal.vault` (personal machine). This machine currently
has no `obsidian-wiki`, no `~/.obsidian-wiki/config`, and no `~/Documents/obsidian`,
but does have Node v22.14.0 — so the skill (incl. optional QMD) is immediately
useful here.

## Objective

boss-skills' `agent-harness` plugin gains a `setup-second-brain` skill
(SKILL.md + stdlib-only PEP 723 script + co-located tests) that installs/configures
obsidian-wiki and optional QMD semantic search, plus the supporting doc/env/version
updates — all defaulting the vault to `~/Documents/obsidian/personal.vault`.

## Problem Statement

The second-brain capability lives only in aif-skills. boss-skills has no
obsidian-wiki integration and no way to bootstrap a second brain from the
agent-harness plugin. It should, matching aif-skills feature-for-feature but with
a personal (not work) default vault.

## Solution Approach

Straight port of the aif-skills feature-second-brain diff into the boss-skills
layout, adapting three environment-specific things:

1. **Path**: aif's plugin is `plugins/agent-harness/`; boss-skills' is
   `plugins/boss-dev/agent-harness/`.
2. **Env-var docs location**: aif has `plugins/ENVIRONMENT_VARIABLES.md`;
   boss-skills has none — env vars are documented in the plugin's
   `docs/getting-started.md`, so the `OBSIDIAN_*`/`QMD_*` tables go there.
3. **Default vault**: `work.vault` → `personal.vault` everywhere it appears.

The skill's split of responsibilities is preserved verbatim: deterministic,
idempotent, offline file edits live in `scripts/setup_second_brain.py`
(stdlib-only PEP 723, `detect` + `apply` subcommands, backup-before-write,
`--dry-run` unified diffs); all network/global installs (`uv tool install`,
`npm install -g @tobilu/qmd`, `obsidian-wiki setup`, `qmd` indexing) and all user
interaction stay in `SKILL.md`, driven via Bash after confirmation.

## What the aif-skills branch changed (captured)

New skill (ported as-is except the default vault value):

- `skills/setup-second-brain/SKILL.md` — explicit-invocation skill
  (`disable-model-invocation: true`), `allowed-tools` for `uv tool`, `uv run`,
  `npm install`, `obsidian-wiki`, `qmd`, `node`, `AskUserQuestion`;
  `argument-hint: "[--apply | --dry-run]"`, `effort: medium`. 8-step workflow:
  detect → summarize → AskUserQuestion decisions → installs → `--dry-run` preview
  → apply QMD config → optional index → report. Uses `${CLAUDE_SKILL_DIR}` for the
  script path (matches boss-skills' sibling `setup-agent-harness`).
- `skills/setup-second-brain/scripts/setup_second_brain.py` — stdlib-only PEP 723
  script. `detect` prints a JSON state report (config + vault existence, which
  `QMD_*` keys are set, `qmd` MCP presence, env readiness incl. Node ≥ 22); `apply`
  writes `QMD_TRANSPORT/QMD_WIKI_COLLECTION/QMD_PAPERS_COLLECTION/QMD_CLI_SEARCH_MODE`
  into `~/.obsidian-wiki/config` (idempotent KEY="value" merge) and, only for
  `--transport mcp`, additively merges a `qmd` MCP server into `~/.claude/settings.json`.
  Backup-before-write with timestamped `.backup.<ts>`, `--dry-run` returns per-file
  unified diffs and writes nothing, invalid `settings.json` aborts before touching
  the config (fail-fast), post-write JSON re-validation restores from backup on failure.
- `skills/setup-second-brain/scripts/tests/test_setup_second_brain.py` +
  `conftest.py` — config parse/merge idempotency, MCP add/preserve/idempotent/
  invalid-json-abort/dry-run, `_node_major` parametrize, detect & apply CLI. conftest
  inserts the scripts dir on `sys.path`.

Doc / config / version edits (adapted to boss-skills):

- `.env.sample` — add `OBSIDIAN_VAULT_PATH` + commented `QMD_*` block.
- `CLAUDE.md` — add a "Second Brain (obsidian-wiki)" section.
- `README.md` — add a "Second Brain (obsidian-wiki)" section.
- aif's `plugins/ENVIRONMENT_VARIABLES.md` `OBSIDIAN_*` + `QMD_*` tables → **put into
  `plugins/boss-dev/agent-harness/docs/getting-started.md`** (boss-skills has no
  ENVIRONMENT_VARIABLES.md).
- agent-harness `README.md`, `docs/skills.md`, `docs/getting-started.md` — skill
  count bump, new `setup-second-brain` rows/sections, Node ≥ 22 dependency note.
- Version bump in `plugin.json` + `marketplace.json` plus a `second-brain` tag.
  **boss-skills current version is `0.13.1` → bump to `0.14.0`.**

## Relevant Files

Source of truth (read-only reference):

- `~/dev/adobe-aifoundations/aif-skills` @ `feature-second-brain` — the four new
  files + the doc/config diffs (`git diff main...feature-second-brain`).

### New Files (in boss-skills)

- `specs/second-brain.md` — this spec.
- `plugins/boss-dev/agent-harness/skills/setup-second-brain/SKILL.md`
- `plugins/boss-dev/agent-harness/skills/setup-second-brain/scripts/setup_second_brain.py`
- `plugins/boss-dev/agent-harness/skills/setup-second-brain/scripts/tests/test_setup_second_brain.py`
- `plugins/boss-dev/agent-harness/skills/setup-second-brain/scripts/tests/conftest.py`

### Modified Files (in boss-skills)

- `.env.sample` — append `OBSIDIAN_VAULT_PATH=~/Documents/obsidian/personal.vault` + commented `QMD_*`.
- `CLAUDE.md` — new "Second Brain (obsidian-wiki)" section (personal.vault default).
- `README.md` — new "Second Brain (obsidian-wiki)" section (personal.vault default).
- `plugins/boss-dev/agent-harness/docs/getting-started.md` — `OBSIDIAN_*`/`QMD_*`
  env-var tables + Node ≥ 22 dep row + skill count.
- `plugins/boss-dev/agent-harness/README.md` — skill count, setup-second-brain bullet.
- `plugins/boss-dev/agent-harness/docs/skills.md` — TOC/at-a-glance row + full `### setup-second-brain` section.
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — `0.13.1` → `0.14.0`.
- `.claude-plugin/marketplace.json` — agent-harness entry `0.13.1` → `0.14.0` + `second-brain` tag.

Reuse / precedent (do not reinvent):

- `plugins/boss-dev/agent-harness/skills/setup-agent-harness/{SKILL.md,scripts/setup_harness.py,scripts/tests/}`
  — identical shape (explicit skill + stdlib PEP 723 `detect`/`apply` + backups +
  co-located `scripts/tests/` + `${CLAUDE_SKILL_DIR}`). Mirror its conventions.
- `version-bump-reviewer` skill (`.claude/skills/version-bump-reviewer/`) — confirm
  the 0.14.0 tier and keep plugin.json/marketplace.json in parity.

## Step by Step Tasks

1. **Save the spec** — write this document to `specs/second-brain.md`.
2. **Copy the skill body (verbatim)** — copy the four aif files into
   `plugins/boss-dev/agent-harness/skills/setup-second-brain/`.
3. **Retarget the default vault** — in `SKILL.md`, replace every
   `~/Documents/obsidian/work.vault` with `~/Documents/obsidian/personal.vault`.
   The script has no hard-coded vault default (grep for `work.vault` → zero hits).
4. **Env sample + top-level docs** — `.env.sample`, `CLAUDE.md`, `README.md`
   second-brain sections, every vault example using `personal.vault`.
5. **Env-var reference** — add the `OBSIDIAN_*` and `QMD_*` tables to
   `plugins/boss-dev/agent-harness/docs/getting-started.md` (`personal.vault`
   default) + a `node ≥ 22 + npm` dependency row.
6. **agent-harness plugin docs** — plugin `README.md` skill count + bullet;
   `docs/skills.md` TOC/at-a-glance row + full section; verify the real current
   skill count in boss-skills.
7. **Version bump + marketplace parity** — `plugin.json` and `marketplace.json`
   `0.13.1` → `0.14.0`, add `second-brain` tag. Confirm tier with `version-bump-reviewer`.
8. **Guard the SKILL.md parser bug** — no `!`-backtick patterns inside fenced
   blocks; all command examples use `$ command` notation.
9. **Validate** — run the validation commands below until clean.

## Testing Strategy

- **Unit (ported)**: the co-located `scripts/tests/` suite runs under `make test`
  (`pyproject.toml` `testpaths = ["tests","plugins"]`, `--import-mode=importlib`),
  covering config parse/merge idempotency, MCP add/preserve/idempotent/invalid-JSON-abort,
  dry-run-writes-nothing, `_node_major` parsing, and `detect`/`apply` CLI exit codes.
- **Manual smoke (offline, safe)** on this machine (no obsidian-wiki installed yet):
  - `detect` prints JSON with `obsidian_wiki.installed=false`, `node.meets_min=true`
    (v22.14.0), `config_exists=false`.
  - `apply --qmd-config --transport cli --dry-run` prints a `qmd_config.diff` and
    writes nothing; re-running `apply` (no dry-run) against a temp `--config-path`
    is idempotent (second run `changed:false`, no new backup).
- **Edge cases** already covered by the port: invalid `~/.claude/settings.json`
  (mcp transport aborts before writing the config), missing config file (created
  with parents, no spurious backup), Node < 22 (QMD skipped, Grep still works).

## Acceptance Criteria

- `setup-second-brain` skill exists under `plugins/boss-dev/agent-harness/skills/`
  with SKILL.md + script + co-located tests, functionally identical to aif-skills.
- Every default vault reference is `~/Documents/obsidian/personal.vault`; **zero**
  occurrences of `work.vault` anywhere in the boss-skills tree.
- `OBSIDIAN_*`/`QMD_*` env vars documented in the plugin's `docs/getting-started.md`;
  `.env.sample`, `CLAUDE.md`, `README.md`, plugin `README.md`, and `docs/skills.md`
  all updated with correct skill counts.
- `plugin.json` and `marketplace.json` both at `0.14.0`, in parity, with the
  `second-brain` tag added.
- `specs/second-brain.md` exists.
- `make lint`, `make test`, and `make markdown-lint` pass with zero warnings/errors.

## Validation Commands

Execute from `/Users/bossjones/dev/bossjones/boss-skills`:

- `git -C ~/dev/adobe-aifoundations/aif-skills diff main...feature-second-brain --stat` — reconfirm the source scope.
- `grep -rn "work.vault" . --include="*.md" --include="*.py" | grep -v .venv` — must return **nothing**.
- `grep -rn "personal.vault" plugins .env.sample CLAUDE.md README.md specs/second-brain.md` — confirms the new default landed.
- `uv run plugins/boss-dev/agent-harness/skills/setup-second-brain/scripts/setup_second_brain.py detect` — valid JSON state report.
- `uv run plugins/boss-dev/agent-harness/skills/setup-second-brain/scripts/setup_second_brain.py apply --qmd-config --transport cli --search-mode quality --dry-run --config-path /tmp/ow.config` — prints a diff, writes nothing.
- `make lint` — ruff + basedpyright clean (covers `plugins/`).
- `make test` — pytest green, incl. the new co-located `setup-second-brain` suite.
- `make markdown-lint` — SKILL.md/docs pass markdown linting.

## Notes

- QMD is strictly optional; a declined-QMD or Node-too-old run still yields a
  fully working Grep-based obsidian-wiki. Never hard-fail on QMD absence.
- obsidian-wiki and qmd stay **global** tools — never add them to `pyproject.toml`
  / `uv sync`. No new Python deps: the script is stdlib-only.
- Alternative considered: create a dedicated `plugins/ENVIRONMENT_VARIABLES.md`
  (matching aif's structure) instead of folding the tables into `getting-started.md`.
  Rejected because getting-started.md is where boss-skills currently documents env
  vars, so this keeps them together.
