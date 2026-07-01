# Obsidian-Wiki as a Second Brain

**Version 1.0.0** · boss-skills · 2026-07-01 · HADS 1.0.0 · Source: <https://github.com/ar9av/obsidian-wiki>

---

## AI READING INSTRUCTION

Read `[SPEC]` and `[BUG]` blocks for authoritative facts — these are verified against
a live install of obsidian-wiki 2026.6.9 + QMD 2.5.3 on this machine.
Read `[NOTE]` only if additional context on intent is needed.
`[?]` blocks are unverified — treat with lower confidence.
The `[BUG]` blocks correct the upstream README, which is stale in several places.

---

## 1. What It Is

**[SPEC]**

- obsidian-wiki implements Andrej Karpathy's **LLM-Wiki pattern**: distill knowledge
  once into interconnected Obsidian markdown pages and keep them current, instead of
  re-asking an LLM the same questions.
- It is a **global CLI tool** that installs a set of *agent skills* into your AI
  coding agents (Claude Code, Codex, Gemini, Copilot, Pi, and others). The skills do
  the actual ingest/query/maintenance work; the CLI just installs and configures them.
- The knowledge lives in one **vault** (an Obsidian folder of `.md` files). Agents
  read raw sources, distill them into pages, and evolve a knowledge graph over time.

**[NOTE]**
The core value is a durable, cross-project memory. From any repo you can push what you
learned into the vault (`/wiki-update`) and pull relevant context before a task
(`/wiki-query`). The vault is plain markdown — portable, git-syncable, and readable
without any tooling.

---

## 2. Install

**[SPEC]**

This repo treats obsidian-wiki as a **global uv tool** — never a project dependency.

```bash
uv tool install obsidian-wiki
obsidian-wiki setup --vault ~/Documents/obsidian/personal.vault
uv tool upgrade obsidian-wiki   # later upgrades
```

- `setup` writes `~/.obsidian-wiki/config` and symlinks the bundled skills into every
  detected agent's skill directory (`~/.claude/skills/`, `~/.codex/skills/`, etc.).
- Verify with `obsidian-wiki info` and `obsidian-wiki list`.

**[BUG] Upstream README says `pip install obsidian-wiki`**
Symptom: following the README installs into a project/global pip env and tempts you to
add it to `pyproject.toml`.
Cause: the README documents the generic distribution; this repo standardizes on uv.
Fix: use `uv tool install obsidian-wiki`. It is a global CLI, not a repo dependency —
do **not** add it to `pyproject.toml` or `uv sync` (per `CLAUDE.md`).

**[BUG] The `[graph,ast]` extras no longer exist in 2026.6.9**
Symptom: `uv tool install "obsidian-wiki[graph,ast]"` prints
`warning: The package obsidian-wiki==2026.6.9 does not have an extra named 'ast'` (and
`'graph'`).
Cause: older docs (including this repo's `CLAUDE.md`) reference extras that were
removed in current releases.
Fix: install without extras — `uv tool install obsidian-wiki`. The warnings are
harmless and the base tool installs fully.

---

## 3. CLI Surface

**[SPEC]**

The CLI has exactly three subcommands (`setup` is the default).

| Command | Purpose |
|---------|---------|
| `obsidian-wiki setup` | Install skills into agents and write config |
| `obsidian-wiki list` | List the bundled skills |
| `obsidian-wiki info` | Show install paths, version, config, per-agent install status |
| `obsidian-wiki -V` / `--version` | Print version (e.g. `obsidian-wiki 2026.6.9`) |

`setup` flags:

| Flag | Meaning |
|------|---------|
| `--vault PATH` | Absolute path to your Obsidian vault |
| `--project [DIR]` | Also install project-local skills + bootstrap files into DIR (defaults to cwd) |
| `--project-only` | Skip the global agent install (use with `--project`) |
| `--copy` | Copy skill files instead of symlinking to the installed package |

---

## 4. Configuration

**[SPEC]**

- Authoritative config: `~/.obsidian-wiki/config` — shell-style `KEY="value"` lines.
  The vault path lives here, **not** in an env var.
- Keys written by a real `setup` + QMD apply on this machine:

```bash
OBSIDIAN_VAULT_PATH="/Users/you/Documents/obsidian/personal.vault"
OBSIDIAN_WIKI_REPO="/…/site-packages/obsidian_wiki/_data"
OBSIDIAN_WIKI_VERSION="2026.6.9"
QMD_TRANSPORT="cli"
QMD_WIKI_COLLECTION="wiki"
QMD_PAPERS_COLLECTION="papers"
QMD_CLI_SEARCH_MODE="quality"
```

- **Multi-vault routing**: create named configs `~/.obsidian-wiki/config.NAME`, switch
  the active one with `/wiki-switch NAME`, and override a single request inline with
  `@name` (e.g. `wiki-query @work what do I know about X`).
- `OBSIDIAN_RAW_DIR` overrides the staging directory (defaults to `_raw`).

---

## 5. Three-Layer Architecture

**[SPEC]**

Knowledge flows through three layers:

1. **Raw sources** — anything ingested (markdown, PDFs, URLs, chat/agent-history
   exports, transcripts, images). Unpromoted captures stage in `_raw/`.
2. **Wiki** — distilled, interconnected pages: concepts, entities, claims, and typed
   relationships (`[[wikilinks]]`); noise dropped.
3. **Schema** — structure emerges and evolves from the content; no fixed upfront design.

- **Delta tracking**: `.manifest.json` logs every ingested source and computes deltas,
  so only new/changed material is reprocessed (no re-ingestion).
- **Provenance**: extracted facts are tagged (`extracted`, `inferred`, `ambiguous`).

---

## 6. The Bundled Skills

**[SPEC]**

`setup` installs 35 skills. They are invoked automatically by description, or manually
as slash commands. Grouped by function:

**Ingest**

| Skill | Purpose |
|-------|---------|
| `wiki-ingest` | Distill any document/text/URL/folder into pages (catch-all) |
| `wiki-update` | Push the current project's learnings into the vault |
| `wiki-research` | Autonomous multi-round web research, filed into the vault |
| `wiki-setup` / `wiki-rebuild` | Initialize a vault / archive+rebuild or restore |

**Query & explore**

| Skill | Purpose |
|-------|---------|
| `wiki-query` | Answer questions from the vault, with citations + multi-hop link walks |
| `wiki-status` | Ingested vs pending delta; `insights` mode surfaces hubs/bridges/orphans |
| `wiki-digest` | Human-readable "what I learned this week" newsletter |
| `wiki-context-pack` | Token-bounded context slice for a downstream agent |
| `memory-bridge` | Browse/diff knowledge by which AI tool produced it |

**Maintain**

| Skill | Purpose |
|-------|---------|
| `wiki-lint` | Audit broken links, orphans, contradictions (`--consolidate` to fix) |
| `cross-linker` | Discover and insert missing `[[wikilinks]]` (write-heavy) |
| `wiki-dedup` | Merge pages covering the same concept under different names |
| `tag-taxonomy` | Enforce a controlled tag vocabulary |
| `wiki-synthesize` | Create synthesis pages for concepts that co-occur but aren't linked |
| `daily-update` | Daily maintenance cycle (freshness, index, `hot.md`) |

**Capture**

| Skill | Purpose |
|-------|---------|
| `wiki-capture` | Save the current conversation as a page; `--quick` stages to `_raw/` |
| `wiki-stage-commit` | Review/promote staged pages (when `WIKI_STAGED_WRITES=true`) |

**Export / import / visualize**

| Skill | Purpose |
|-------|---------|
| `wiki-export` / `wiki-import` | Graph ↔ JSON/GraphML/Neo4j/HTML/OKF bundles |
| `graph-colorize` | Color-code the Obsidian graph view by tag/category/visibility |
| `wiki-dashboard` | Dynamic Bases/Dataview dashboard views of the vault |
| `vault-skill-factory` | Turn mature vault pages into a portable Agent Skill |

**Agent-history ingest** — mine past sessions of a coding agent into the vault:

| Skill | Source |
|-------|--------|
| `claude-history-ingest` | `~/.claude` conversations |
| `codex-history-ingest` | `~/.codex` sessions |
| `copilot-history-ingest` | GitHub Copilot CLI sessions |
| `hermes-history-ingest` | `~/.hermes` memories |
| `openclaw-history-ingest` | `~/.openclaw` sessions |
| `pi-history-ingest` | `~/.pi/agent/sessions` |
| `wiki-history-ingest` / `wiki-agent` | Router + query-driven topic ingest (`/wiki-claude X`, `/wiki-codex X`, …) |

**Multi-vault**: `wiki-switch` manages named vault profiles.

---

## 7. QMD Semantic Search (Optional)

**[SPEC]**

QMD (`@tobilu/qmd`) upgrades `wiki-query` / `wiki-ingest` from Grep to on-device
semantic (lex + vec) search. Strictly optional — the skills degrade to Grep silently
when unset.

- Requires **Node ≥ 22**. Install: `npm install -g @tobilu/qmd`.
- Config keys (in `~/.obsidian-wiki/config`): `QMD_WIKI_COLLECTION`,
  `QMD_PAPERS_COLLECTION`, `QMD_TRANSPORT` (`cli` | `mcp`), `QMD_CLI_SEARCH_MODE`
  (`quality` | `balanced` | `fast`).
- Index a vault into a collection, then embed:

```bash
qmd collection add ~/Documents/obsidian/personal.vault --name wiki
qmd embed
qmd status            # verify: documents indexed + vectors embedded
qmd collection list
```

- Query directly: `qmd query "how does X work" -c wiki`.

**[BUG] README's `qmd index --name wiki <vault>` command is outdated**
Symptom: `qmd index …` does not create the collection on QMD 2.5.3.
Cause: the indexing subcommand changed; the README documents an older QMD.
Fix: use `qmd collection add <vault> --name wiki` **then** `qmd embed`. The first
`qmd embed` downloads a ~333 MB embedding model (`embeddinggemma-300M`), so it takes
~30s+ on first run. Confirm with `qmd status` / `qmd collection list`.

**[BUG] README example sets `QMD_TRANSPORT=mcp`; this repo defaults to `cli`**
Symptom: choosing `mcp` edits `~/.claude/settings.json` and needs a Claude Code reload;
copying the README verbatim can be surprising.
Cause: the README shows `mcp`; the boss-skills `setup-second-brain` path defaults to
`cli`.
Fix: prefer `cli` transport — it touches **only** `~/.obsidian-wiki/config`, needs no
reload, and supports the `quality`/`balanced`/`fast` search modes. Use `mcp` only if
you specifically want the QMD MCP server (`qmd mcp`).

---

## 8. Core Workflows

**[SPEC]**

Use the brain from any project:

```bash
cd ~/projects/my-app && claude
> /wiki-query <topic>       # pull context before starting a task
> /wiki-update              # distill this project's learnings into the vault
```

Capture then promote:

```bash
/wiki-capture --quick               # save conversation findings to _raw/
/wiki-ingest promote my raw pages   # promote _raw/* into proper pages
```

Keep the graph coherent:

```bash
/wiki-lint                 # audit broken links, orphans, contradictions
/cross-linker              # auto-weave missing [[wikilinks]]
/tag-taxonomy              # normalize the tag vocabulary
```

Sync the vault to GitHub (optional): `git init` the vault, add a remote, and run
`~/.obsidian-wiki/sync.sh` (optionally on an hourly cron) to commit + push.

---

## 9. Verified Setup On This Machine

**[SPEC]**

Confirmed working configuration (2026-07-01):

- obsidian-wiki **2026.6.9** installed via `uv tool install`; 35 skills symlinked into
  `~/.claude/skills/` (and 11 other agent skill dirs).
- Vault: `~/Documents/obsidian/personal.vault`.
- QMD **2.5.3** on Node **v22.14.0**; transport `cli`, search mode `quality`.
- Collection `wiki` created from the vault and embedded (`qmd status` → documents
  indexed, vectors embedded).
- `~/.claude/settings.json` untouched (cli transport); config write is idempotent and
  backed up before each change.

**[NOTE]**
A fresh vault has almost nothing to match semantically. Ingest real sources
(`/wiki-update`, `/wiki-ingest`, the `*-history-ingest` skills), then re-run
`qmd embed` (or `qmd update`) to keep embeddings current.

---

## 10. Changelog

**[SPEC]**

- **Version 1.0.0** (2026-07-01) — Initial HADS document. Covers install (uv-tool),
  CLI surface, config, three-layer architecture, all 35 skills, QMD integration,
  workflows, and the verified local setup. Includes four `[BUG]` blocks correcting the
  stale upstream README (`pip install`, `[graph,ast]` extras, `qmd index`, and the
  `mcp` transport default).
