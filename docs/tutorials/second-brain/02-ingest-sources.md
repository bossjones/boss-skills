# Tutorial: Feed the brain at scale

**Time:** ~15 minutes · **Level:** beginner · **Reference:** [obsidian-wiki reference](../../../ai_docs/obsidian_wiki.md)

In guide 01 you proved the loop works: one URL or file in, one distilled page out. That's the
smallest unit of work `wiki-ingest` does. This guide covers the rest of what it can swallow — single
documents, whole folders, raw chat exports, and even your own past coding sessions in other agents —
plus the staging workflow and the delta tracking that keeps repeated ingests from creating
duplicates.

## Prerequisites

| You need | Check it |
|----------|----------|
| `obsidian-wiki` installed and set up | `obsidian-wiki info` prints a version, not an error |
| Guide 01 completed (at least one ingest done) | `/wiki-status` shows more than zero pages |
| Claude Code running in any project | any `claude` session — skills work from anywhere |

## Step 1 — Ingest a single structured document

Start with the case you already know: one file. `wiki-ingest` handles markdown, PDFs, saved
articles, and plain notes the same way — read it, distill the durable concepts, write one or more
linked pages.

```text
> ingest this file: /path/to/paper.pdf
```

or, for a local markdown note:

```text
> ingest this file: ~/notes/meeting-notes.md
```

For long PDFs you don't need the whole document — tell it which pages matter:

```text
> ingest pages 12-30 of /path/to/paper.pdf
```

The skill reads only that range, so a 300-page book doesn't turn into one giant, unfocused page.

## Step 2 — Ingest a web URL

Paste a link and say what you want done with it. `wiki-ingest` fetches the page, strips the
boilerplate, distills the content, and files a page under the right topic:

```text
> add this to my wiki: https://example.com/some-article-you-like
```

or invoke the skill directly:

```text
/wiki-ingest https://example.com/some-article-you-like
```

If the article overlaps with something already in the vault, the new page links to it instead of
duplicating the explanation — that's the cross-linking behavior kicking in automatically during
ingest, not a separate step you have to run.

## Step 3 — Ingest a whole folder

Once single files feel slow, point the skill at a directory instead. This is the same operation,
just batched:

```text
> ingest this folder: ~/notes
```

Every file in the folder is read and distilled in turn. Because of the delta tracking covered in
Step 7, running this again later after adding two new files to `~/notes` only processes the two
new ones — everything already in the vault is skipped, not re-ingested.

## Step 4 — Ingest raw, unstructured text

Not every source is a clean document. `wiki-ingest` also handles messy exports: chat logs, Slack or
Discord threads, meeting transcripts, journal entries, or a CSV/JSON dump you exported from
somewhere. Paste it or point at the file and describe what it is:

```text
> process this export: ~/Downloads/slack-export-2026-06.json
```

```text
> here's a meeting transcript, pull out anything worth keeping: [paste text]
```

The skill's job here is noisier than a structured document: most of a chat log is chit-chat, and
only a fraction is durable knowledge. Expect fewer output pages than input lines — that's the
distillation working as intended, not the skill missing content.

## Step 5 — Mine your own agent history

This is the source type that's easy to forget: you already have a knowledge base sitting on disk in
every coding agent you've used. A family of history-ingest skills turns those sessions into vault
pages:

| Skill | Source folder |
|-------|----------------|
| `claude-history-ingest` | `~/.claude` |
| `codex-history-ingest` | `~/.codex` |
| `copilot-history-ingest` | GitHub Copilot CLI session store |
| `hermes-history-ingest` | `~/.hermes` |
| `openclaw-history-ingest` | `~/.openclaw` |
| `pi-history-ingest` | `~/.pi/agent/sessions` |

Run one directly to bulk-process everything new since last time:

```text
> process my Claude history
```

```text
> ingest my Codex sessions
```

`wiki-history-ingest` is the router — invoke it without naming a specific agent and it figures out
which history skills apply on this machine and runs them.

If you don't want a bulk sweep, and instead want just the sessions about one topic, use the
query-driven variant:

```text
/wiki-claude re-authentication token refresh
```

```text
/wiki-codex flaky pytest fixture
```

`/wiki-claude` and `/wiki-codex` (and their siblings for the other agents) search that agent's raw
history for the topic, ingest only the matching sessions, and hand you back a synthesized answer you
can use immediately — cross-referencing what you already solved elsewhere, rather than archiving
everything.

## Step 6 — Stage now, promote later

Sometimes you want to save a finding fast without waiting for the full distillation pass — mid-debug,
between meetings, or when a session-end hook fires automatically. That's what the `_raw/` staging
area is for:

```text
/wiki-capture --quick
```

This drops the finding straight into `_raw/` with no manifest write and no index update — it's
intentionally cheap. Those staged notes sit there until you're ready to fold them into the real
wiki:

```text
> promote my raw pages
```

or:

```text
/wiki-ingest promote my raw pages
```

Promotion runs the staged notes through the same distillation `wiki-ingest` applies to any other
source, then links and files the resulting pages properly. Nothing in `_raw/` is a permanent home —
think of it as an inbox.

## Step 7 — Understand delta tracking

Every source you feed the wiki — a file, a URL, a folder, a history session — gets logged in a
`.manifest.json` file inside the vault. On every ingest, the skill diffs what's proposed against
that manifest and computes a delta: only new or changed material gets processed. Re-running
`ingest this folder: ~/notes` after nothing has changed does no work at all; re-running it after
adding one file processes just that file.

Facts extracted from a source also carry a provenance tag, so you can tell how confident a claim is
just by reading the page:

- `extracted` — stated directly in the source.
- `inferred` — reasonably concluded, but not stated outright.
- `ambiguous` — the source was unclear; flagged for you to verify.

### Before and after

A raw source goes in — say, a rambling meeting transcript that mentions a decision to switch a
service's caching layer. What comes out is a small, linked, tagged page like this:

```markdown
# Redis Cache Migration Decision

## Summary

The team decided to replace the in-memory cache with Redis to fix cache invalidation bugs
across multiple app instances. [inferred] Rollout is planned in two phases.

## Related

- [[Caching Strategy]]
- [[Service Architecture]]

## Tags

#decision #infrastructure #caching
```

The transcript's small talk, scheduling logistics, and tangents are gone. What survives is the
durable decision, tagged, linked to related pages, and marked with its confidence level — exactly
the pattern `wiki-ingest` applies to every source type in this guide.

One more thing worth knowing before you move on: if QMD semantic search is configured on your
machine, ingest uses it for a smarter similarity pass when deciding what to link; otherwise it falls
back to plain Grep matching, which still works, just less precisely. Guide 05 and the
[reference](../../../ai_docs/obsidian_wiki.md) cover setting QMD up.

## Next steps

You can now feed the vault from documents, URLs, folders, raw text, and your own agent history —
and you understand why re-running an ingest never duplicates work. From here:

- [03 — Query your brain](03-query-your-brain.md) covers asking the vault questions and pulling
  context back out of everything you just fed it.
- Back to the [README](README.md) for the full five-part series.
