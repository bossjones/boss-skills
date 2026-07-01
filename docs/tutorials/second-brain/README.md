# Tutorial series: Get started with your second brain

A hands-on, task-first series for actually *using* the [`obsidian-wiki`](https://github.com/ar9av/obsidian-wiki)
second brain — a knowledge vault that AI agents build and query for you. Where the
[setup tutorial](../agent-harness/second-brain.md) gets obsidian-wiki installed and configured, this
series picks up from a working (but empty) vault and takes you through the full lifecycle: first
steps, feeding it, querying it, keeping it current, and maintaining it as it grows.

**Level:** beginner → intermediate · **Reference:** [obsidian-wiki reference](../../../ai_docs/obsidian_wiki.md)

## Before you start

You need a working obsidian-wiki install. If you don't have one yet, run the
[Set up your second brain](../agent-harness/second-brain.md) tutorial first, then come back here.

Verify it's ready:

```text
$ obsidian-wiki info
```

## The mental model

Everything in this series revolves around three layers. Knowledge flows left to right; you mostly
touch the first layer, and the wiki emerges from there.

```text
  raw sources            wiki                       schema
  (what you feed)        (what agents distill)      (what emerges)
  ─────────────          ────────────────────       ──────────────
  docs, PDFs, URLs,  →   interconnected pages:   →   structure grows
  chat/agent history     concepts, entities,        from the content;
  staged in _raw/        claims, [[wikilinks]]      no upfront design
```

- **Ingest** raw sources; agents **distill** them into linked pages and drop the noise.
- `.manifest.json` tracks every source, so re-ingesting only processes what changed.
- You query the wiki from any project — the payoff of everything you fed in.

## Which guide do I need?

| I want to… | Start here |
|------------|------------|
| I just set up an empty vault — what now? | [01 — Take the first steps in an empty vault](01-empty-vault-first-steps.md) |
| Add documents, URLs, folders, or past agent sessions | [02 — Feed the brain at scale](02-ingest-sources.md) |
| Ask questions and pull context into any project | [03 — Query your second brain](03-query-your-brain.md) |
| Keep the vault fresh as I work day to day | [04 — Keep your vault current with the update loop](04-keep-it-current.md) |
| Clean up, connect, and scale a vault that has grown | [05 — Maintain and scale your second brain](05-maintain-and-scale.md) |

## The guides

1. **[Take the first steps in an empty vault](01-empty-vault-first-steps.md)** — Confirm the install,
   internalize the three-layer model, and run your first ingest and capture to see the smallest
   possible knowledge loop produce real pages.
2. **[Feed the brain at scale](02-ingest-sources.md)** — Ingest documents, web URLs, whole folders,
   raw text/exports, and your own past agent sessions; understand `_raw/` staging and delta tracking.
3. **[Query your second brain](03-query-your-brain.md)** — Ask natural-language questions with
   citations, use fast index-only mode, trace multi-hop connections, and see how QMD semantic search
   changes results.
4. **[Keep your vault current with the update loop](04-keep-it-current.md)** — The recurring habits:
   `/wiki-update`, `/wiki-capture`, `/wiki-status`, `/daily-update`, refreshing QMD embeddings, and
   when to append versus rebuild.
5. **[Maintain and scale your second brain](05-maintain-and-scale.md)** — Periodic hygiene
   (`wiki-lint`, `cross-linker`, `tag-taxonomy`, `wiki-dedup`, `wiki-synthesize`), multi-vault
   profiles, and export/visualization.

Work through them in order the first time — each guide builds on the vault state the previous one
leaves behind. After that, use the table above to jump to whatever you need.

## Reference

- [obsidian-wiki reference](../../../ai_docs/obsidian_wiki.md) — the full CLI surface, config schema,
  three-layer architecture, all 35 bundled skills, and QMD semantic search.
- [Set up your second brain](../agent-harness/second-brain.md) — the one-time install/setup walkthrough.
- Back to [all tutorials](../README.md).
