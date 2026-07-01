# Tutorial: Keep your vault current with the update loop

**Time:** ~15 minutes · **Level:** intermediate · **Reference:** [obsidian-wiki reference](../../../ai_docs/obsidian_wiki.md)

A knowledge base only pays off if it stays current. A vault frozen at the day you set it up is
just a snapshot — the value comes from a recurring habit of pushing what you learn back in, and
occasionally pulling the index and embeddings up to date so search actually finds it. This guide
covers that update loop: the small, repeatable moves you make during and after real work, day to
day.

## Prerequisites

| You need | Check it |
|----------|----------|
| A working vault with content already in it | `/wiki-status` shows at least a few ingested pages |
| Claude Code running in any project | any `claude` session — the wiki skills work from anywhere |
| QMD configured (optional, for Step 5) | `qmd status` runs without error |

## Step 1 — Push project learnings from wherever you are

The core "sync from wherever you are" move is `/wiki-update`. Run it from inside any repo you've
been working in — it distills what you just did in *that* project into the vault:

```text
$ cd ~/projects/my-app && claude
```

```text
> /wiki-update
```

`wiki-update` looks at the current project context — recent changes, decisions, gotchas you
worked through — and writes or updates the corresponding wiki pages. You don't copy files by hand;
you just run this at natural breakpoints (after a task, before switching context, at the end of a
session).

If you keep more than one vault, route the update to a named one inline instead of switching your
active vault first:

```text
> @work update wiki
```

The `@work` prefix targets the `work` named config for this one call only (see the multi-vault
setup in `~/.obsidian-wiki/config.work`), leaving your default vault untouched.

## Step 2 — Capture in the moment

`wiki-update` distills a project; `/wiki-capture` distills a *conversation*. Use it right after a
discussion that produced real insight — a debugging session, a design decision, an explanation you
don't want to re-derive later:

```text
> /wiki-capture
```

This is not a transcript dump. The skill classifies what was discussed and rewrites it as
declarative knowledge — "X works like this because Y" — then files it in the right place in the
vault, ready to be linked from other pages.

When you don't have a full minute to spare, use quick mode:

```text
> /wiki-capture --quick
```

`--quick` stages a fast finding straight to `_raw/` in under a minute — no manifest update, no
index rewrite, just get it out of your head and onto disk. This is also what the session-end Stop
hook uses to auto-preserve findings you might otherwise lose.

Staged notes in `_raw/` aren't full wiki pages yet. Promote them later, in a batch, when you have
a moment to review:

```text
> /wiki-ingest promote my raw pages
```

## Step 3 — Read the delta before you decide what to do

Before every ingest session, check what's actually pending. `/wiki-status` reports what's already
ingested versus what's changed or new since the last pass:

```text
> /wiki-status
```

Use this output to decide your next move: if the delta is small, append (an ordinary
`/wiki-update` or `/wiki-ingest` run will fold it in cleanly). If the delta is large or the
report shows contradictions piling up, that's a signal to look harder before you keep appending —
more on that trigger in Step 6.

Treat `/wiki-status` as a recurring checkpoint, not a one-time check. Run it at the start of any
session where you plan to feed the vault something.

## Step 4 — Run the daily maintenance cycle

Beyond per-project updates, the vault needs a daily housekeeping pass. `/daily-update` runs that
cycle in one shot: it checks the freshness of every ingested source, refreshes the top-level
index, and regenerates `hot.md` (the vault's "what matters right now" page):

```text
> /daily-update
```

Run it manually whenever you like, but it's designed to be automated: wire it to a launchd cron
(for example, a 9 AM trigger) with a morning terminal notification, so the vault is always
current before you start your first session of the day. The `daily-update` skill itself can set
up that cron and notification infrastructure if you ask it to.

## Step 5 — Keep QMD embeddings fresh

If you've configured QMD for semantic search, ingesting new pages is only half the job — a page
that exists in the vault but isn't embedded won't surface in semantic `/wiki-query` results. It's
invisible to search even though it's sitting right there in Obsidian.

After any significant ingestion (a batch of `/wiki-update` runs, a promoted `_raw/` batch, a
history-ingest pass), refresh the index and the vectors:

```text
$ qmd update
$ qmd embed
$ qmd status
```

`qmd update` re-indexes the collection against the current vault contents (add `--pull` first if
the vault is a git repo you sync elsewhere, to pull remote changes before re-indexing). `qmd embed`
recomputes vectors for anything new or changed. `qmd status` confirms both counts — documents
indexed and vectors embedded — so you know the refresh actually took.

Skipping this step is the single most common reason "I just added that but the wiki can't find
it" happens. Ingest writes the page; embed makes it searchable.

## Step 6 — When to append versus when to rebuild

Most days, you append. `/wiki-update`, `/wiki-ingest`, and `/wiki-capture` all add to the existing
graph incrementally, and that's the right default — the vault's value is cumulative.

Reach for `/wiki-rebuild` only when the vault has drifted far enough from its sources that
patching it up piecemeal stops being worth it — heavy duplication, stale pages nothing links to
anymore, a structure that no longer matches how you actually work. `wiki-rebuild` archives the
current vault and rebuilds it from scratch (or restores a previous archive if a rebuild went
wrong):

```text
> /wiki-rebuild
```

Treat this as a rare, deliberate reset, not a routine maintenance step — it's the "start over
carefully" option, not part of the daily loop.

## Step 7 — A realistic end-of-session flow

Here's how the pieces above chain together on an ordinary day. You finish a task, close the loop,
and the knowledge is there the next time you need it — in any project, not just this one:

```text
> /wiki-update
```

```text
$ qmd embed
```

```text
$ cd ~/projects/other-app && claude
```

```text
> /wiki-query how did I solve the retry-backoff issue last time
```

Finish the task, push the learning in (`/wiki-update`, or `/wiki-capture` if it was a
conversation-shaped insight), refresh the embeddings so it's searchable, and move on. The next
time you're in a completely different repo and hit something related, `/wiki-query` pulls it back
— that's the whole payoff of keeping the loop running.

## Next steps

You now have the recurring habits that keep a vault alive: push learnings as you go, capture
conversations in the moment, check the delta before big ingests, run daily maintenance, keep
embeddings fresh, and reserve rebuilds for rare resets.

- [05 — Maintain and scale](05-maintain-and-scale.md) covers the deeper maintenance skills —
  linting, deduplication, tag taxonomy, and cross-linking — for when the vault grows large enough
  to need active curation.
- Back to the [README](README.md) for the full five-part series.
