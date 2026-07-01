# Tutorial: Query your second brain

**Time:** ~15 minutes · **Level:** beginner · **Reference:** [obsidian-wiki reference](../../../ai_docs/obsidian_wiki.md)

Ingesting is only half the loop. The payoff shows up when you pull knowledge back out — in the
middle of unrelated work, from a project that has nothing to do with where the knowledge came
from. This guide covers `wiki-query`, the skill that answers questions from your compiled vault
with citations, plus the exploration skills that sit next to it: fast index-only lookups,
multi-hop connection tracing, named-vault routing, and how QMD semantic search changes what comes
back.

## Prerequisites

| You need | Check it |
|----------|----------|
| A vault with a few ingested pages (from [02 — Ingest sources](02-ingest-sources.md)) | `/wiki-status` shows more than zero pages |
| Claude Code running in any project | any `claude` session — `wiki-query` works from anywhere |
| QMD installed (optional, for Step 5) | `qmd status` prints indexed documents, not "command not found" |

## Step 1 — Ask your first question

Open Claude Code in any project — it does not need to be the project the knowledge came from —
and ask a plain-language question:

```text
$ cd ~/some-other-project
$ claude
```

```text
> /wiki-query what do I know about rate limiting strategies
```

`wiki-query` reads the relevant pages in your vault and answers in prose, then cites which pages
it drew from. A realistic answer looks like this:

```text
You've explored three approaches: token-bucket (simple, bursty traffic tolerant),
sliding-window-log (precise, memory-heavier), and a fixed-window counter you flagged
as having edge-boundary problems. Your notes lean toward token-bucket for public APIs
and sliding-window for internal billing-sensitive endpoints.

Sources: [[rate-limiting-strategies]], [[token-bucket-algorithm]], [[api-gateway-design]]
```

The citations are real wikilinks — open any of them in Obsidian to read the full page and see
what else it connects to. If the answer feels thin, that usually means the topic hasn't been
ingested yet, not that the skill failed — go back to `/wiki-ingest` first.

## Step 2 — Get a fast answer when you don't need the full read

Reading every full page body takes longer and costs more tokens than you need for a quick sanity
check. Ask for speed explicitly and `wiki-query` switches to an index-only mode that answers from
page summaries and frontmatter instead of full bodies:

```text
> quick answer: have I looked into websocket reconnection before?
```

```text
> just scan the vault, don't read the pages — do I have anything on OAuth PKCE?
```

Any of "quick answer", "just scan", "don't read the pages", or "fast lookup" trigger this mode.
You get a shorter, coarser answer faster — good for "have I touched this before, yes or no"
checks before you decide whether a deeper query is worth it.

## Step 3 — Trace connections between two things

Some of the most useful questions aren't "what do I know about X" but "how does X relate to Y".
`wiki-query` walks the typed edges between pages across multiple hops to answer these:

```text
> how is connection pooling connected to the timeout bug we found last month
```

```text
> trace the chain from the auth-service redesign to the incident postmortem
```

```text
> what does the recommendation-engine depend on, transitively
```

A multi-hop answer reads like a path, not a single fact:

```text
connection-pooling -> exhausted-under-load -> timeout-bug-2026-04 -> retry-storm
-> circuit-breaker-added

Four hops. The pooling change wasn't the direct cause of the timeout bug, but it
removed the headroom that let a retry storm exhaust connections during the incident.
```

Phrases like "how is X connected to Y", "what links X to Y", "trace the chain from X to Z", and
"what does X depend on transitively" all signal this mode. It's the query type that turns a flat
pile of notes into an actual graph you can reason over.

## Step 4 — Query a specific named vault

If you maintain more than one vault profile (covered in depth in
[05 — Maintain and scale your second brain](05-maintain-and-scale.md)), you don't have to switch your
active profile just to ask one question. Prefix the query with `@name` to route it inline:

```text
> wiki-query @work what do I know about the Q3 migration plan
```

The `@work` override applies to that single query only — your default vault is untouched, and the
next `/wiki-query` you run (without a prefix) goes back to it. This is the fast path for "let me
peek at my other vault without switching contexts."

## Step 5 — Understand how QMD changes what comes back

`wiki-query` behaves differently depending on whether QMD semantic search is configured
(`qmd status` reports indexed documents and embedded vectors) or not.

- **Without QMD**, `wiki-query` falls back to Grep — it matches on the words you actually typed.
  Ask about "RSC" and it only finds pages that literally contain "RSC".
- **With QMD configured**, `wiki-query` runs a concept-level (lexical + vector) pass first. Ask
  about "RSC" and it can surface a page titled `React Server Components` even though the acronym
  never appears in your query or, potentially, in the page title itself — the match happens on
  meaning, not just characters.

Practically: QMD matters most when your vocabulary drifts — you ask with an acronym but wrote the
page out in full, or vice versa. Without it, keyword mismatches just come back empty.

You can also bypass `wiki-query` entirely and hit QMD directly, which is useful for debugging
whether a disappointing answer is a retrieval problem or a synthesis problem:

```text
$ qmd query "how does the retry backoff work" -c wiki
```

If the direct QMD query surfaces the right pages but `wiki-query`'s prose answer still misses the
point, the problem is in how the answer was composed, not in what was found.

## Step 6 — Explore beyond a single question

A handful of related skills round out "using the brain" beyond one-off Q&A:

- `wiki-status` in `insights` mode — surfaces hub pages (heavily linked), bridge pages
  (connecting otherwise-separate clusters), and orphan pages (nothing links to them).
- `wiki-digest` — generates a "what I learned this week" newsletter-style summary from recent
  vault activity.
- `wiki-context-pack` — builds a token-bounded slice of relevant context you can hand directly to
  another agent or paste into a different tool.
- `memory-bridge` — browse and diff knowledge by which AI tool originally produced it (useful for
  "what does Codex know that Claude doesn't").

You don't need to memorize these — reach for them when a plain `/wiki-query` isn't the right
shape for what you're trying to see.

## Step 7 — Querying is how the ingesting pays off

Every guide before this one was about getting knowledge in. This one is the return on that
investment: from any repo, on any day, you open Claude Code and pull relevant context in one
line before you write a line of code. That's the whole point of the second brain — not a bigger
pile of files, but a faster start on tomorrow's problem because today's you already wrote it down.

## Next steps

- [04 — Keep it current](04-keep-it-current.md) covers the maintenance skills that keep the graph
  coherent as it grows — linting, cross-linking, deduping, and daily updates.
- Back to the [README](README.md) for the full five-part series.
