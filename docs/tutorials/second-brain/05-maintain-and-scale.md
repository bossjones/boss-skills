# Tutorial: Maintain and scale your second brain

**Time:** ~25 minutes · **Level:** intermediate · **Reference:** [obsidian-wiki reference](../../../ai_docs/obsidian_wiki.md)

Your vault has grown past the "one page, one link" stage from the earlier guides — you've
ingested sources, captured conversations, and queried it back. Left alone, a growing wiki
accumulates the same mess a growing codebase does: broken links, orphaned pages, duplicate
concepts under different names, and drifting tags. This guide is not a one-time setup — it's the
recurring maintenance loop you run *periodically* as the vault scales, plus the skills for
managing more than one vault and getting knowledge out of Obsidian entirely.

## Prerequisites

| You need | Check it |
|----------|----------|
| A vault that's grown to many pages (past guides 01–04) | `/wiki-status` reports dozens of pages, not just a couple |
| `obsidian-wiki` installed and skills symlinked | `obsidian-wiki info` prints a version and vault path |
| Comfort running `/wiki-ingest`, `/wiki-capture`, `/wiki-query` | you've completed the earlier guides in this series |
| A second vault path ready (optional, for Step 6) | not required — Step 6 shows how to create one |

## Step 1 — Audit health with wiki-lint

Start every maintenance pass with a report, not a fix. Run:

```text
> /wiki-lint
```

`wiki-lint` scans the whole vault and reports, without changing anything: broken `[[wikilinks]]`
that point at pages which don't exist (or were renamed), orphan pages with no incoming or
outgoing links, contradictions between pages that make conflicting claims, and stale content that
hasn't been touched in a long time. Read the report before you decide what to do next — on a
vault this size, some of it may be expected (a deliberately standalone reference page isn't a
bug).

When you're ready to act instead of just read, add `--consolidate`:

```text
> /wiki-lint --consolidate
```

This switches `wiki-lint` from report-only into a "dream cycle": it fixes broken links,
cross-references orphan pages back into the graph, corrects outdated lifecycle states, normalizes
tag aliases, and adds contradiction callouts where two pages disagree. It shows a dry-run preview
of every change first and asks for explicit confirmation before it writes anything — so a
`--consolidate` run is still safe to try, you just have to say yes to the batch of edits it
proposes.

## Step 2 — Weave connections with cross-linker

`wiki-lint` reports orphans; `cross-linker` is the write-heavy skill that fixes them by inserting
the missing `[[wikilinks]]` themselves:

```text
> /cross-linker
```

It scans every page for concepts, entities, and phrases that match other pages in the vault and
adds the cross-reference where one is missing. Run this right after any large ingest — new pages
land as islands until something links them into the existing graph, and `cross-linker` is that
something. Skipping it after a big batch ingest is the single most common reason a vault ends up
full of disconnected pages.

## Step 3 — Normalize tags with tag-taxonomy

Tags sprawl fast once several people (or several sessions of you) are adding pages: `#llm`,
`#llms`, `#large-language-models` all describing the same thing. `tag-taxonomy` enforces one
controlled vocabulary:

```text
> /tag-taxonomy
```

Use it two ways: reactively, to audit and fix tag drift across the whole vault, and proactively,
by consulting it *whenever* you or a skill is about to create or update a page — check the
taxonomy first so a new page uses the existing tag instead of inventing a synonym. The tags are
metadata for later filtering and dashboards (Step 7), so keeping them controlled now saves a much
bigger cleanup later.

## Step 4 — Merge duplicates with wiki-dedup

Even with tags under control, the same *concept* can end up as two separate pages with different
titles — "RSC" from one ingest and "React Server Components" from another. `wiki-dedup` finds and
merges these:

```text
> /wiki-dedup
```

This is page-level and destructive — it combines two pages into one and removes the redundant
file — so it confirms carefully before merging anything, showing you which pages it believes
cover the same concept and what the merged result will look like. Review its proposed matches;
don't rubber-stamp a merge between pages that only sound similar.

## Step 5 — Synthesize new knowledge with wiki-synthesize

The previous steps clean up what already exists. `wiki-synthesize` creates something new: it
looks for concepts that co-occur across multiple pages but that no single page connects, and
writes a new synthesis page that draws the cross-cutting conclusion those pages imply together.

```text
> /wiki-synthesize
```

This is most useful once the vault has real breadth — a handful of pages rarely produce
interesting synthesis, but dozens of pages ingested from different sources over weeks often
contain conclusions that were never written down explicitly anywhere. Run it as a periodic
"connect the dots" pass, not on every session.

## Step 6 — Manage multiple vaults with wiki-switch

If you keep a personal brain and a work brain separate, manage them as named profiles instead of
juggling one giant vault. Each profile is its own config file at `~/.obsidian-wiki/config.NAME`.

Check which profile is active, or list what's available, with no argument:

```text
> /wiki-switch
```

Activate a different profile:

```text
> /wiki-switch work
```

Every skill in this series also accepts an inline `@name` override for a single request, without
switching the active profile at all:

```text
> wiki-query @work what do I know about the deployment pipeline
```

Use `wiki-switch` when you're settling in to work in one vault for a while, and the inline `@name`
form when you just need to peek at (or write to) another vault for one request.

## Step 7 — Export, import, and visualize

Once the vault holds real knowledge, get it out of Obsidian-only markdown when you need to.
`wiki-export` writes the graph in several formats, all under a `wiki-export/` folder:

```text
> /wiki-export
```

Choose JSON or GraphML for tooling, a Neo4j Cypher script to load into a graph database, an
interactive HTML view to share without installing anything, or an OKF markdown bundle for
portability. To load an export (or an OKF bundle from someone else) into another vault, use:

```text
> /wiki-import
```

Two more skills round out visualization and packaging. `graph-colorize` rewrites the Obsidian
graph view's color groups by tag, category, or visibility so the graph is readable at a glance
instead of a wall of identical dots — it always backs up `graph.json` before touching it:

```text
> /graph-colorize
```

`wiki-dashboard` builds dynamic Bases/Dataview views over the vault (think: a live table of every
page tagged `#project`, sorted by last-updated), and `vault-skill-factory` goes a step further —
it turns a cluster of mature, curated pages into a portable, self-contained Agent Skill you can
share or install elsewhere:

```text
> /wiki-dashboard
```

```text
> /vault-skill-factory
```

## Step 8 — Set your maintenance cadence

You don't run all of the above every day. Match the skill to how often the underlying problem
recurs:

| Cadence | Run |
|---------|-----|
| Daily | `/daily-update` — freshness check, index refresh, `hot.md` regeneration |
| After every big ingest | `/cross-linker`, then `qmd embed` if you use QMD semantic search |
| Monthly (or when the vault feels messy) | `/wiki-lint --consolidate`, `/wiki-dedup`, `/wiki-synthesize` |

Treat this table as the default rhythm, not a rigid schedule — if `wiki-status` shows a spike of
orphans right after a big history ingest, run `cross-linker` immediately instead of waiting for
the monthly pass.

## Next steps

You now have the full loop: ingest and capture feed the vault, query gets knowledge back out, and
this guide's skills keep it healthy as it scales into hundreds of pages and multiple vaults.

- Back to the [README](README.md) for the full five-part series.
- Revisit [Set up your second brain](../agent-harness/second-brain.md) if you're setting up a new
  machine or a teammate's environment from scratch.
