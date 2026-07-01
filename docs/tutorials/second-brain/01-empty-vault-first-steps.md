# Tutorial: Take the first steps in an empty vault

**Time:** ~10 minutes · **Level:** beginner · **Reference:** [obsidian-wiki reference](../../../ai_docs/obsidian_wiki.md)

You just finished installing and configuring `obsidian-wiki`. Your vault exists, the skills are
symlinked into Claude Code, and the folder is completely empty. That blank-page moment is normal —
this guide runs your very first session end to end: confirm the install, understand the mental
model, ingest one thing, capture one thing, and see the result in Obsidian.

## Prerequisites

| You need | Check it |
|----------|----------|
| `obsidian-wiki` installed and set up (separate tutorial) | `obsidian-wiki info` prints a version, not an error |
| A vault path configured | `obsidian-wiki info` shows a `vault` path |
| Claude Code running in any project | any `claude` session — skills work from anywhere |
| The Obsidian app (optional, for Step 6) | installed and pointed at your vault folder |

## Step 1 — Confirm the setup is live

Before you add anything, prove the plumbing works. Run these from any shell:

```text
$ obsidian-wiki info
```

You'll see the installed version, the resolved vault path (on this machine that's
`~/Documents/obsidian/personal.vault`), and a per-agent skill install status table — Claude Code
should show as installed.

```text
$ obsidian-wiki list
```

This prints every bundled skill (`wiki-ingest`, `wiki-query`, `wiki-capture`, and the rest). You
don't need to memorize the list — you'll meet the important ones as you use them.

If `info` errors out or shows no vault path, the setup step didn't complete — go back to the
setup tutorial before continuing here.

## Step 2 — Understand the mental model first

Resist the urge to start creating folders and tags. `obsidian-wiki` is built around a three-layer
pattern (Karpathy's LLM-Wiki), and understanding it now saves you from over-organizing later:

1. **Raw sources** — anything you feed in: URLs, markdown files, PDFs, conversation transcripts,
   agent history. Unpromoted captures stage in a `_raw/` folder inside the vault.
2. **Wiki** — the actual product: distilled, interconnected pages written in plain Obsidian
   markdown, connected with `[[wikilinks]]`. Noise gets dropped; only the durable knowledge
   survives.
3. **Schema** — the folder structure, tags, and categories that *emerge* from the content over
   time. There is no upfront design to get right on day one.

A `.manifest.json` file in the vault tracks every source that's already been ingested, so
re-running an ingest on the same source is a no-op instead of a duplicate.

The practical takeaway: your job right now is only to feed layer 1. The skills handle layers 2
and 3.

## Step 3 — Check the starting state

Open (or switch to) any project directory and start Claude Code, then ask for the wiki's status:

```text
$ cd ~/some-project
$ claude
```

```text
> /wiki-status
```

On a brand-new vault, this reports almost nothing ingested — no pages, an empty or missing
`_raw/`, nothing pending. That's the expected, correct answer for an empty vault. `wiki-status` is
your recurring checkpoint: you'll run it again in later guides to see the vault grow.

## Step 4 — Do your first tiny ingest

Now feed the wiki one real thing. Pick something small: a URL you like, or a single markdown file
on disk. Either invoke the skill directly or just describe what you want in plain language:

```text
> /wiki-ingest
```

or, without the slash:

```text
> add this to my wiki: https://example.com/some-article-you-like
```

Say what the source is (a URL, a path, pasted text) and let the skill run. It does not copy the
source verbatim into a file — it reads it, extracts the durable concepts, and writes one or more
distilled pages with `[[wikilinks]]` to anything related. If nothing related exists yet (which is
likely, since the vault is empty), you'll just get a clean new page or two.

This is the smallest possible loop in the whole system: one source in, one or more pages out.
Everything else in this series builds on repeating it.

## Step 5 — Do your first capture

Ingest handles external sources; capture handles the conversation you're already having. Try it
now, on this very session:

```text
> /wiki-capture
```

The skill classifies what you just discussed, rewrites it as declarative knowledge (not a chat
log — think "X works like this" rather than "I asked about X and you said..."), and files it into
the right place in the vault.

If you just want to stash a quick finding without the full write-up, use quick mode:

```text
> /wiki-capture --quick
```

`--quick` drops a fast note straight into `_raw/` with no manifest or index update — useful for
bugs and gotchas you want to promote into a real page later.

## Step 6 — See the result

Open your vault folder in the Obsidian app (the same path from `obsidian-wiki info`, e.g.
`~/Documents/obsidian/personal.vault`). You should see:

- One or more new `.md` pages from your Step 4 ingest and Step 5 capture.
- The graph view showing those pages as nodes — with a fresh vault, expect just a couple of dots,
  maybe connected by one link.

Every page is plain markdown. You can open, read, and edit it in any text editor, not just
Obsidian — there is no proprietary format or lock-in.

## Step 7 — What not to do first

A quick warning before you move on: don't spend your first session designing folders, tag
schemes, or a category hierarchy. The schema in this system *emerges* from what you ingest — the
skills (`tag-taxonomy`, `wiki-lint`, `cross-linker`) exist precisely to clean up and organize
structure after content exists, not before. On day one, your only job is to keep feeding it real
sources and captures. Structure will follow.

## Next steps

You've proven the loop works: ingest or capture something, and a page appears. From here:

- [02 — Ingest sources](02-ingest-sources.md) covers feeding the vault at scale — URLs, files,
  folders, and agent history — instead of one item at a time.
- Back to the [README](README.md) for the full five-part series.
