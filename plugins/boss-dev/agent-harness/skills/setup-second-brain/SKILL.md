---
name: setup-second-brain
description: Install and configure the "second brain" — the obsidian-wiki uv tool plus optional QMD semantic search. Use when setting up a second brain, installing obsidian-wiki, making a machine "second-brain ready", configuring an Obsidian knowledge vault for AI agents, or enabling/configuring QMD semantic search (QMD_WIKI_COLLECTION, QMD_TRANSPORT). Detects what is already present, previews every change, then installs obsidian-wiki[graph,ast] as a uv tool, runs obsidian-wiki setup against the vault, optionally installs QMD via npm, writes QMD variables to the config, and can index the vault. Every config file is backed up before it is written.
disable-model-invocation: true
allowed-tools:
  - Bash(uv tool:*)
  - Bash(uv run:*)
  - Bash(npm install:*)
  - Bash(obsidian-wiki:*)
  - Bash(qmd:*)
  - Bash(node:*)
  - AskUserQuestion
argument-hint: "[--apply | --dry-run]"
effort: medium
---

# Setup second brain

Bootstraps the obsidian-wiki "digital brain" and, optionally, QMD semantic search
on this machine. obsidian-wiki is a global uv tool that maintains an Obsidian
markdown vault (Karpathy's LLM-Wiki pattern). QMD is an optional on-device search
engine that upgrades `wiki-query` / `wiki-ingest` from Grep to concept-level
matching; the wiki skills degrade to Grep silently when QMD is not configured.

Two kinds of work are cleanly separated:

- **Deterministic config edits** live in `scripts/setup_second_brain.py` (stdlib-only
  PEP 723). It writes the `QMD_*` variables into `~/.obsidian-wiki/config` and — only
  for `mcp` transport — merges a `qmd` MCP server into `~/.claude/settings.json`.
  Every file is backed up first; `--dry-run` shows a unified diff and writes nothing.
- **Global installs** (`uv tool install`, `npm install -g`, `obsidian-wiki setup`,
  `qmd` indexing) are run by this skill via Bash, only after the user confirms.

This skill owns all user interaction. Never install or index without confirmation,
and never overwrite a config without showing the diff first.

## Workflow

### 1. Detect current state (read-only)

```text
$ uv run "${CLAUDE_SKILL_DIR}/scripts/setup_second_brain.py" detect
```

This prints a JSON report: whether `~/.obsidian-wiki/config` exists and its
`OBSIDIAN_VAULT_PATH`, whether that vault directory exists, which `QMD_*` keys are
already set, whether a `qmd` MCP server is in `~/.claude/settings.json`, and an
`env` block with the presence/version of `uv`, `node` (and whether it meets the
Node 22 minimum QMD needs), `npm`, `obsidian-wiki`, and `qmd`.

### 2. Summarize findings

If `settings_error` is non-null, `~/.claude/settings.json` is unreadable (invalid
JSON) and `mcp_qmd_configured` is reported as `null`. Surface the error and tell the
user to fix or remove the file before choosing `mcp` transport — `apply` refuses to
overwrite it anyway. `cli` transport is unaffected.

Otherwise, tell the user in plain language: whether obsidian-wiki is installed,
whether the vault exists, which `QMD_*` keys are already set, and any `env` hints
(these are advisory). Call out explicitly if `node.meets_min` is false — QMD cannot
be installed until Node 22 or newer is on PATH.

### 3. Collect decisions with AskUserQuestion

Ask only for what `detect` leaves undecided:

- **Install obsidian-wiki** — if `obsidian_wiki.installed` is false, confirm running
  `uv tool install "obsidian-wiki[graph,ast]"`.
- **Vault path** — default `~/Documents/obsidian/personal.vault`. If a vault is already
  configured, offer to keep it or point at a different path.
- **Enable QMD** — optional. Offer Yes / No. If `node.meets_min` is false, note that
  QMD will be skipped until Node 22 or newer is installed, and continue without it.
- **QMD transport** (only if QMD enabled) — `cli` (default; no settings.json change)
  or `mcp` (adds a `qmd` MCP server to `~/.claude/settings.json`). For `cli`, also
  offer the search mode: `quality` (rerank, default), `balanced`, or `fast`.
- **Index the vault now** (only if QMD enabled) — offer to build the QMD collection
  from the vault after setup.

### 4. Run the installs (after confirmation)

Run only the steps the user approved. obsidian-wiki first:

```text
$ uv tool install "obsidian-wiki[graph,ast]"
$ obsidian-wiki setup --vault ~/Documents/obsidian/personal.vault
```

For QMD, guard on the Node version before installing — QMD needs Node 22 or newer:

```text
$ node --version
$ npm install -g @tobilu/qmd
```

If Node is older than 22, skip QMD with a clear message (e.g. suggest `fnm use 22`
or installing a newer Node) and proceed with a fully working Grep-based setup.

### 5. Preview the config diff with --dry-run

Always preview before writing. Run the same `apply` you intend to run, plus
`--dry-run`: nothing is written and each touched file carries a `diff` field.

```text
# cli transport (writes only ~/.obsidian-wiki/config)
$ uv run "${CLAUDE_SKILL_DIR}/scripts/setup_second_brain.py" apply --qmd-config --transport cli --search-mode quality --dry-run
```

```text
# mcp transport (also merges the qmd MCP server into ~/.claude/settings.json)
$ uv run "${CLAUDE_SKILL_DIR}/scripts/setup_second_brain.py" apply --qmd-config --transport mcp --dry-run
```

Show the `qmd_config.diff` (and `mcp.diff` for `mcp` transport) to the user in a
`diff`-highlighted fenced block and confirm before applying. A `changed: false`
result means that file is already in the desired state.

### 6. Apply the QMD config

Drop `--dry-run` to write. Use `--wiki-collection` / `--papers-collection` to
override the defaults (`wiki` / `papers`) if the user picked different names.

```text
$ uv run "${CLAUDE_SKILL_DIR}/scripts/setup_second_brain.py" apply --qmd-config --transport cli --search-mode quality
```

The script backs up `~/.obsidian-wiki/config` (and `settings.json` for `mcp`) before
writing and reports the backup paths. Skip this step entirely if the user declined QMD.

### 7. Index the vault (optional)

If the user chose to index and `qmd` is installed, build the collection from the
vault. Confirm the exact subcommands first with `qmd --help`, then:

```text
$ qmd collection add ~/Documents/obsidian/personal.vault --name wiki
$ qmd embed
```

Use the same collection name written to `QMD_WIKI_COLLECTION`. For `mcp` transport,
start the server with `qmd mcp` (or `qmd mcp --http --daemon`) and note that Claude
Code must reload to pick up the new MCP server.

### 8. Report

Relay: what was installed (`obsidian-wiki info`, `qmd --version`), which `QMD_*`
keys were written and the backup paths, whether the vault was indexed, and — for
`mcp` transport — that `~/.claude/settings.json` gained a `qmd` server and a reload
is needed. If QMD was skipped (declined or Node too old), say so plainly and confirm
the wiki still works with Grep.

## Notes

- QMD is strictly optional. A declined-QMD or Node-too-old run still yields a fully
  working obsidian-wiki setup — never hard-fail on QMD absence.
- `cli` transport touches only `~/.obsidian-wiki/config`. Only `mcp` transport edits
  `~/.claude/settings.json`, and only via an additive, backed-up merge that preserves
  other MCP servers. Invalid JSON there aborts the apply and writes nothing.
- Nothing is written without a backup first, and the config write is idempotent —
  re-running with the same choices produces no diff and no new backup.
- obsidian-wiki and qmd stay global tools; never add them to `pyproject.toml` or
  `uv sync`. Upgrade later with `uv tool upgrade obsidian-wiki` and
  `npm update -g @tobilu/qmd`.
- All command examples are deliberately prefixed with a dollar sign and space — the
  skill parser executes exclamation-backtick patterns even inside fenced code blocks
  (see `.claude/rules/skill-development.md`).
