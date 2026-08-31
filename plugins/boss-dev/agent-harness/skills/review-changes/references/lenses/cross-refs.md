# Lens: cross-refs

`theme: "cross-refs"`. Everything that points **out** of the changed file — links, indexes, and
the sibling documents that must move with it.

Run every gate in `quality-gates.md`. Return only the JSON in `observation-format.md`.

## Domain

Relative links, file pointers, index/readme entries, and any parallel catalogs the repo
maintains. Anchors *within* the changed file belong to `structure`; whether a claim is *true*
belongs to `claims`.

## The checks

**Relative links resolve.** Every `](../foo/bar.md)` and `](./baz.md)` must exist at the path
given, from the linking file's directory. A doc that moved and left its inbound links behind is
the same defect. Check both directions when the diff renames or moves a file:

```bash
git diff "$MB" --name-status | grep -E '^R'      # renames
grep -rn "old/path/name.md" --include=*.md .     # who still points at it
```

**Index drift.** Detect the indexing convention rather than assuming one. Look for the nearest
`README.md` up the directory tree from a new or moved file, a docs-site nav
(`mkdocs.yml`, `SUMMARY.md`, `docusaurus.config.*`, `_sidebar.md`), and any index file the repo
profile's `## Index files` section names explicitly (`references/repo-profile.md`). A new file
that should appear in one of these and does not is a finding.

**Two-rule-file drift, if discovery found more than one.** If Step 2 discovered two distinct
rule files (different blob ids) that each maintain their own catalog of the same thing — for
example a `CLAUDE.md` and a separate `AGENTS.md` that each list available skills — a new entry
added to one and not the other is a finding. A rule changed in one that the other now
contradicts is `consistency`'s job, not this lens's; this lens covers the catalog-entry gap
specifically.

**Reference paths cited by bare filename.** Inside a skill or agent-config directory, a
`references/*.md` cited by **bare filename** resolves from neither the referencing file's
directory nor the repo root. The dispatching file must pass an absolute path, or the referenced
file is silently never opened — and the agent still returns well-formed output, so the failure
is invisible. Flag a skill or config body that cites a reference by bare name with no
arrangement to pass the absolute path.

**Stale file pointers.** A "Key files" table, a `> **Source:**` line, or prose that names a file
the diff moved, renamed, or deleted. A doc pointing at a CLI command or script the repo's own
declared entrypoints no longer define.

**Downstream renders.** Some repos declare a canonical file with downstream copies (a wiki page,
a generated site, an exported doc) — see the repo profile's `## Downstream renders` section. A
substantive change to the canonical file with no note that the downstream copies are now stale
is a MEDIUM.

## Categories

`broken-link`, `missing-index-entry`, `catalog-drift`, `unresolvable-reference-path`,
`stale-file-pointer`, `orphaned-inbound-link`, `stale-downstream-render`.

## Evidence bar

The link exactly as written, the path it resolves to, and the result of checking that path.
For an index finding: the file added and the index that does not mention it, by path and line.
For catalog drift: both statements, both files, both line numbers.

## Do not report

An external URL you could not reach (network failures are not findings — say so at LOW). A link
that resolves. An index entry the diff did not need to create. Preference about link text or
whether a link should be relative or absolute.
