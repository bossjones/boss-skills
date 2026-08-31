# Lens: structure

`theme: "structure"`. The navigational scaffolding of a document — section refs, anchors,
heading sequence, table shape, and a changelog convention if the repo has one.

Run every gate in `quality-gates.md`. Return only the JSON in `observation-format.md`.

This lens is **mechanical on purpose**. Measure, then report only what the diff itself broke.
Everything here has a right answer you can compute, so a finding without a computation is not a
finding.

## Domain

Intra-file structure. Everything that points *out* of the file belongs to `cross-refs`.

## The checks

**`§N` refs and in-file anchors.** Some repos cross-reference heavily as `[§12.3](#123-…)`.
Renumbering or retitling a section silently breaks every one of them, and the renderer shows a
dead link with no error. For each `](#anchor)` in the diff, resolve it against the headings in
the same file under GitHub's slug rules:

```bash
# headings -> their GitHub anchor slugs
grep -n '^#\{1,6\} ' <file> | sed 's/^\([0-9]*\):#* //' | \
  tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9 -]//g; s/ /-/g'
# every in-file anchor referenced
grep -o '](#[^)]*)' <file> | sort -u
```

Slug rules that matter: lowercase, spaces -> `-`, punctuation dropped, **emoji dropped**, `§`
dropped. A heading with emoji or a section number needs its slug computed, not guessed.

A bare `§12.3` in prose with no link is fine; a `§12.3` that names a section which no longer
exists is a finding regardless of linking.

**Heading sequence.** Duplicate section numbers. A gap the doc does not explain. A `###` under
no `##`. A section number in the body that does not match the heading it sits under.

**Changelog convention, if one is discovered.** If the discovered rules (Step 2 /
`references/repo-profile.md`) establish that documents in this location carry a changelog
section, flag a document with none and flag a substantive content change that did not add a
dated line to an existing one. Where no such convention is discovered, do not invent one.

**Table shape.** A row whose cell count does not match the header. A column added to the header
and not to the rows. A table whose alignment row is malformed — it renders as literal text and
nobody notices in the diff.

**Doc shape.** A brand-new document that lands very large (say past ~2,000 lines) with no table
of contents or "how to read this" section is worth a MEDIUM as a shape finding — say it as
shape, not as a cap violation, unless the discovered rules actually set a line cap.

## Priority depends on who caused it

This is the whole judgement of this lens, and getting it wrong makes the lens noise:

- **The diff broke it** — renumbered a section, retitled a heading, added the malformed row ->
  MEDIUM, HIGH when the broken ref is load-bearing navigation in a doc people are being asked
  to read this week.
- **It was already broken before the diff** and the diff only touched the file -> do **not**
  report. That is a pre-existing absence; the challenger rejects it as
  `imputed-pre-existing-absence`. (Full-file mode is the exception — when it is running, say so
  in your evidence and report pre-existing breakage too.)

Always state both states: what the anchor resolved to at the base SHA, what it resolves to now.

## Categories

`broken-section-ref`, `broken-anchor`, `heading-sequence`, `duplicate-section-number`,
`missing-changelog`, `stale-changelog`, `table-shape`, `toc-drift`, `new-doc-shape`.

## Evidence bar

Numbers and strings, always: the anchor as written, the slug it computes to, and the heading
set it failed to match. "The links might be stale" is not a finding.

## Do not report

Markdown style, heading capitalisation, blank-line conventions, list-marker choice, line
length. A long section. An anchor that resolves. Any structure the diff did not change.
