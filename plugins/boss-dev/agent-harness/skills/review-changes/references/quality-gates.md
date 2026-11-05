# Quality gates — what every lens does before it reports

These run inside the lens, before it emits anything. They are why the review is usable: most
bad findings die here, at zero cost to anyone downstream.

## Gate 1 — Diff scope

Report only on lines that appeared as `[N]` in the annotated patch. Content you found via
`Read`/`Grep`/Scout outside the diff is **context only**. `Read` shows *file* line numbers;
the patch shows *diff* line numbers; they are different numbers, and citing the wrong one
gets the finding dropped by the gate.

This bites hardest on large files. A lens that opened the whole file and cited what it saw will
have every finding dropped. Re-read the annotated patch before you write `location.line`.

If the real problem is outside the diff, you have two honest options: anchor the finding to
the diff line that *creates* the problem, or drop it. Do not anchor to an unrelated nearby
line to smuggle it in.

## Gate 2 — Cross-reference

Search the rest of the diff and the repo for a mitigation before you claim a gap: another
changed file that handles it, an index that was updated, a source row that supports the
claim, a section that already qualifies the statement.

**In a long document, check the document itself first.** A claim you think is unsupported is
very often supported three sections away, and a contradiction you think is live is often
resolved by a qualifier you have not read. This is the single most common false positive on
prose.

Addressed elsewhere → drop, or `confidence: LOW` with the reason. Unsure → `MEDIUM` with the
reason. Verified not addressed → `HIGH`.

**Use whatever capability is actually available, and say which you used.** If Scout MCP tools
are present in the session, `mcp__scout__semantic_doc_search` is the right first call for a
markdown claim, with `mcp__scout__keyword_search` / `mcp__scout__regex_search` for exact
literals and `mcp__scout__go_to_definition` / `find_references` for symbol lookups. If they are
not present, fall back to `Grep`/`Glob` and **say so in your evidence** rather than claiming an
index-backed answer you did not get. For a claim about what code elsewhere in the repo actually
does, dispatch a plain subagent for that one question rather than grepping it inline yourself —
it returns a citable verdict without blowing your own context.

## Gate 3 — Platform behaviour

Verify from files, tool output, or docs in the workspace — not from memory. Wherever this content
is headed has behaviour that can turn a plausible finding into a false one:

- **GitHub markdown anchors** — the slug is lowercased, spaces become `-`, punctuation and
  emoji are dropped, `§` is dropped. Compute the slug against the actual heading; do not guess it.
- **Any non-GitHub render target** (a wiki, a docs site, a different markdown renderer) — not
  every markdown construct round-trips identically. If the repo profile (see
  `references/repo-profile.md`) names a downstream render, note what might not survive.
- **An issue tracker** — issue types, states, and custom fields are instance-specific. Look them
  up read-only via whatever the repo profile names; do not assume a field exists.
- **Claude Code vs other agent-CLI frontmatter** — some tools' YAML readers are lenient and
  coerce bad types; others are strict and drop the entire skill on a malformed field. A skill
  that works in one harness may be invisible in another; check the target's own docs rather than
  assuming.

Cite what you read.

## Gate 4 — This repo's rules, read at the base SHA

The compiled rule context you were given came from the merge base — see
`references/repo-profile.md` for how it was discovered. Use it as the top authority, above any
general practice, and **cite the rule by path** — whichever of `CLAUDE.md`, `AGENTS.md`,
`.cursor/rules/`, a nested `README.md`, or a `.claude/review-changes.md` profile entry actually
supplied it.

If the content matches an established pattern in this repo, that is a reason to drop the
finding, not to report a preference. A repo can have deliberate patterns that look wrong out of
context — confidence tags on every claim, long tables as the plan of record, docs that declare a
canonical counterpart elsewhere. The discovered rules and the surrounding documents decide, not
your instinct.

## Gate 5 — Evidence self-check

Ask: **does my evidence support or contradict my claim?**

- Supports → report it.
- Ambiguous → cap at MEDIUM and say what is ambiguous.
- **Contradicts → drop it entirely.**

A finding whose own quoted evidence refutes its point is the most common false positive there
is, and the challenger checks for it first.

## Gate 6 — Is the suggestion real?

If you attach a `suggestion`, its `replaces` text must appear **verbatim in the annotated
patch**, and the replacement must be something this repo would actually accept. Check the
declared entrypoints (`[project.scripts]`, `package.json` `bin`/`scripts`, `Cargo.toml`
`[[bin]]`, `Makefile`/`justfile` targets) for a command that exists, the discovered rules for the
convention, the document's own terminology section for the right name. Suggesting a command that
is not actually declared anywhere, or a folder that violates a discovered placement rule, is
worse than saying nothing. A suggestion that fails this gate gets stripped — the finding survives
without it.

## Gate 7 — Value (required for MEDIUM and above)

All of these must hold, or downgrade to LOW / drop:

- it prevents a real problem or measurably improves the document
- the impact is specific, not "could be better"
- the evidence is more than your opinion
- the suggested action is concrete

## Gate 8 — Is it already someone else's job?

Do not report what a tool already enforces. Detect what the target repo actually runs, in this
order of authority:

1. `.pre-commit-config.yaml` / `lefthook.yml` — what blocks a commit
2. `.github/workflows/*` (or the repo's CI config) — what blocks a merge
3. tool config: `pyproject.toml`, `eslint.config.*`/`.eslintrc*`, `biome.json`, `.prettierrc*`,
   `rustfmt.toml`, `.golangci.yml`, `.rubocop.yml`, `.editorconfig`, a markdown-lint config
4. `Makefile` / `justfile` targets

Whatever those own is not a finding. The repo profile's `## Already enforced` section (see
`references/repo-profile.md`) may name more. **Formatting, import order, frontmatter mechanics,
markdown style, prose typos and grammar: not findings, regardless of whether a tool actually
catches them.**

## The universal skip list

- subjective style preferences with no rule backing
- an alternative structure or framing when the current one works
- educational commentary that names no problem
- "consider expanding this section" with no named gap
- restating what the change does (that is a summary, not a finding)
- a pre-existing absence the diff did not create (see the challenge criteria)
- speculative future needs ("if this doc ever covers N teams…")
- typos, grammar, and word choice
