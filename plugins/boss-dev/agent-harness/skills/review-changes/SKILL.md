---
name: review-changes
description: >
  Multi-lens review of the changes in the current working tree - docs, specs, config, and code -
  before you commit, open a PR, or publish. Dispatches parallel reviewer lenses (claims,
  consistency, structure, cross-refs, placement, disclosure, code) over an annotated diff,
  validates every finding mechanically against a citable-line set so a finding cannot cite a
  line that was not actually changed, then runs an adversarial challenge pass to strip false
  positives before anything is reported. Use when asked to "review my changes", "review this
  before I push", "pre-flight check", "review this diff", "check this before I commit", or before
  committing a unit of work. Learns the target repo's own rules at the merge-base SHA (CLAUDE.md,
  AGENTS.md, .cursor/rules, nested READMEs) plus an optional `.claude/review-changes.md` profile,
  so it works in any repository without hardcoded assumptions about layout or language.
argument-hint: "[staged | unstaged | full | <paths...>] (default: merge base with origin/HEAD -> working tree)"
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Agent
---

# Review the changes in this tree

This repo's own rules are never hardcoded — they are **discovered** at runtime (see
[references/repo-profile.md](references/repo-profile.md)), so the same mechanism works in any
repository.

**The goal is early feedback.** A wrong count, a broken link, or a swallowed error caught here is
one that does not reach a PR, a published doc, or a teammate's review queue.

**On dispatching agents:** fanning out one subagent per lens *is* this skill's mechanism.
Invoking `/review-changes` is the request for it — do not second-guess the dispatch.

## The shape of a run

```text
scope the diff  ->  load repo rules AT BASE SHA  ->  dispatch N lenses in parallel
                ->  validate mechanically  ->  challenge (FP filter)  ->  report
```

Each stage is below. Do not skip the validation stage: it is cheap, it is deterministic, and it
is what keeps this from being a noise generator.

---

## Step 1 - Scope the diff

Default scope is **everything on this branch including the working tree** - the point is to
review what you are about to commit, so committed, staged, unstaged, and untracked changes are
all in scope by default. Honour an explicit narrowing argument (`staged`, `unstaged`, a path
list) when given.

```bash
# Resolve the base as a REMOTE-TRACKING ref when one exists. `--short` already
# yields "origin/main"; do NOT strip the prefix - a bare "main" resolves to the
# LOCAL branch, which is routinely stale, and silently drags already-merged
# upstream commits into the review.
BASE=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null)
for candidate in origin/main origin/master origin/develop origin/trunk; do
  [ -z "$BASE" ] && git rev-parse --verify "$candidate" >/dev/null 2>&1 && BASE=$candidate
done
if [ -z "$BASE" ]; then
  # No remote, or none of the usual names resolved - fall back to a local branch.
  for candidate in main master develop trunk; do
    git rev-parse --verify "$candidate" >/dev/null 2>&1 && BASE=$candidate && break
  done
fi
if [ -z "$BASE" ]; then
  echo "review-changes: cannot resolve a base branch (checked origin/HEAD, common remote and local names)" >&2
  exit 1     # fail loudly: an unresolvable base exits 128 with EMPTY stdout,
fi           # which is indistinguishable from "no changes" if you don't check
MB=$(git merge-base "$BASE" HEAD 2>/dev/null) || MB=""
if [ -z "$MB" ]; then
  # Shallow clone, or no shared history yet (first commit on the repo). Fall
  # back to reviewing staged + unstaged only, and say so in the report.
  MB=HEAD
fi

git diff "$MB" --name-only              # DEFAULT: merge base -> working tree
git diff --staged --name-only           # only if asked for staged
git diff --name-only                    # only if asked for unstaged
git status --porcelain | awk '/^\?\? /{print substr($0,4)}'   # untracked candidates
```

**Every Bash call is a fresh shell - `BASE` and `MB` do not survive between them.** Run the
resolution above and the `git diff` that consumes it *in the same invocation*, or re-resolve
first, or persist the value (`git rev-parse "$MB" > .git/review-changes-base` and read it back).
Never let `$MB` reach `git diff` unset: `git diff ""` exits 128 with **empty stdout**, which is
indistinguishable from a clean tree, and the review then passes a diff it never read.

`git diff "$MB"` (two-dot against the working tree, **not** `"$MB"...HEAD`) covers
committed + staged + unstaged in one pass. `...HEAD` compares two commits and cannot see the
working tree at all, so it would silently review the previous commits and report a clean pass on
the change you are about to commit. If `MB` fell back to `HEAD` (shallow clone, or a repo with no
shared history yet), the scope is staged + unstaged only - state that explicitly in the report.

**Untracked files are a separate pass.** `git diff "$MB"` never sees a file `git status` marks
`??` - verified: a freshly created untracked file produces empty output from
`git diff HEAD --name-only`. For a "review before you commit" skill, a brand-new untracked file
is one of the most important things to catch, not an edge case. Annotate each untracked file
(respecting `.gitignore` - an untracked-but-ignored file stays out of scope) as if it were wholly
new:

```bash
git diff --no-index -- /dev/null <file>
```

This yields a normal `@@ -0,0 +1,N @@` hunk that the same annotator below handles - every line in
the file becomes citable.

**Say in the output which scope was reviewed**, and whether the base fell back from a
remote-tracking ref. If the diff (tracked + untracked) is empty, report "no changes to review"
and stop - but only after the resolution above succeeded, so an empty result means an empty diff
rather than a failed command.

Then capture the diff itself with line numbers the lenses can cite. Generate the annotated patch
per changed file (use the same `"$MB"` so the citable-line set matches the scope):

```bash
git diff "$MB" -- <file> | \
  awk '/^diff --git /{inhunk=0}
       /^@@/{split($3,a,",");ln=substr(a[1],2)-1;inhunk=1;print;next}
       !inhunk{next}                       # never number the diff preamble
       /^\\/{next}                          # "\ No newline at end of file"
       /^\+/{ln++;printf "[%d] %s\n",ln,$0;next}
       /^-/{printf "[--] %s\n",$0;next}
       {ln++;printf "[%d] %s\n",ln,$0}'
```

All three guards matter. Without `!inhunk{next}` the `diff --git` / `index` / `+++` preamble is
numbered `[1] [2] [3]`, which puts three bogus entries in the citable-line set of **every**
file - a hole in the exact gate Step 4 relies on. `!inhunk` alone only covers the *first* file:
`inhunk` stays 1 once set, so the `/^diff --git /{inhunk=0}` reset is what keeps the preamble of
files 2..N out of the set when the patch is generated in one multi-file pass. Without the
`/^\\/` skip, git's `\ No newline at end of file` marker is counted as content and every `[N]`
after it in that hunk is off by one.

`[N]` is the line number in the **new** file - the only number a lens may cite. `[--]` is a
deletion and is not citable. Record the set of citable line numbers per file; Step 4 enforces it.

**Skip these files** (mark them `skipped` in coverage, drop any finding on them):

| Class | Detection |
|---|---|
| Binary | `git diff --numstat` prints `-` for both the added and deleted column |
| Generated | `.gitattributes` `linguist-generated`, plus a portable list: `*.lock`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `uv.lock`, `poetry.lock`, `Cargo.lock`, `go.sum`, `*.min.js`, `*.map`, `*_pb2.py`, `*.generated.*` |
| Vendored / build | `node_modules/`, `vendor/`, `dist/`, `build/`, `target/`, `.venv/`, `venv/`, `__pycache__/`, `coverage/` |
| Profile-supplied | anything named under the target repo's `## Skip paths` section, see [references/repo-profile.md](references/repo-profile.md) |

**Size guard.** If one file's annotated patch exceeds **~150 KB**, chunk it by hunk group and
dispatch that lens once per chunk, merging the results before Step 4. A lens whose context is
blown returns confident nonsense about the half it saw.

**Full-file mode (opt-in).** `/review-changes full <path>` reviews `<path>` in its entirety as if
newly added - every line is citable. Use it to sweep stale counts and broken anchors that predate
the branch. It is **off by default** because it forfeits the pre-existing-absence protection that
keeps the review quiet (see `imputed-pre-existing-absence` in
[references/challenge-criteria.md](references/challenge-criteria.md)), so expect more findings
and weigh them accordingly. Say in the report that full-file mode ran.

## Step 2 - Load the rules THIS repo judges by, at the base SHA

Read rule files from the **merge base**, not the working tree, so a rule edit in your own diff
cannot soften the review of that diff. There is no fixed list of rule files - discover what this
repo actually has:

```bash
BASE_SHA=$(git merge-base "$BASE" HEAD 2>/dev/null || git rev-parse HEAD)

# Root-level rule files, whichever exist at the base SHA
for f in CLAUDE.md AGENTS.md AGENT.md CONTRIBUTING.md .github/copilot-instructions.md; do
  git show "$BASE_SHA:$f" 2>/dev/null
done
git ls-tree -r --name-only "$BASE_SHA" -- .cursor/rules .claude/rules 2>/dev/null

# Nested rules: for every top-level directory the diff touches, also check its
# own rule/readme files - many repos keep conventions next to the content they
# govern rather than only at the root.
git show "$BASE_SHA:<dir>/CLAUDE.md" 2>/dev/null
git show "$BASE_SHA:<dir>/AGENTS.md" 2>/dev/null
git show "$BASE_SHA:<dir>/README.md" 2>/dev/null
```

**Dedupe symlinked rule files by blob id, not by name.** A repo may symlink one rule file to
another (a common pattern is an `AGENT.md` symlink pointing at `CLAUDE.md`, or vice versa).
Compare `git rev-parse "$BASE_SHA:<fileA>"` against `git rev-parse "$BASE_SHA:<fileB>"`: if the
blob ids match, it is one file read once, not two independent sources. This still catches the
important case - two files with *different* blob ids that restate the same conventions and now
disagree is a real `consistency` finding.

**Read the optional per-repo profile.** `git show "$BASE_SHA:.claude/review-changes.md"` -
documented in [references/repo-profile.md](references/repo-profile.md). It sharpens generic
discovery with repo-specific knowledge (issue-tracker key patterns, which tools already gate
which findings, index files that must be updated, and so on) without this skill hardcoding any
of it. **Say in the report whether a profile was found.** Its absence is not an error - the
review is just quieter, which is the correct default when nothing is known.

Rule precedence is strict:

1. **This repo's own rules** - override everything. Cite them by path.
2. **Industry standards** - only where the repo is silent.
3. **Your own judgement** - lowest.

## Step 3 - Dispatch the lenses in parallel

Read `references/lenses/<name>.md` for each lens and dispatch one subagent per lens **in a
single message** so they run concurrently. Pick lenses by what the diff actually touches -
running the `code` lens over a prose-only diff wastes a turn and invites invented findings.

| Lens | Run it when the diff touches | Model |
|---|---|---|
| `claims` | any prose - counts, ticket keys, links, attributions, confidence tags | opus |
| `consistency` | any prose, weighted to long documents | opus |
| `disclosure` | **always** | opus |
| `code` | source files in any language, build scripts, CI workflow files, `.claude/**` or equivalent agent config | opus |
| `structure` | any `.md` | sonnet |
| `cross-refs` | new/moved/renamed files, links, index pages | sonnet |
| `placement` | new/moved/renamed files | sonnet |

Give every lens: the annotated patches, the changed-file list, the citable-line set, the compiled
rule context from Step 2 (including whether a profile was found and what it says), the branch
name, the merge-base SHA (`$MB`, which several lens snippets consume and which does **not**
survive into a subagent's shell), and the **absolute paths of `references/quality-gates.md`,
`references/observation-format.md`, and `references/repo-profile.md`**. Pass those three paths
explicitly: the lens files cite them by bare or repo-relative name, which resolves from neither
`references/lenses/` nor the repo root, and a lens that cannot open `quality-gates.md` skips all
eight gates while still returning well-formed JSON - an invisible failure. Tell each to return
**only** the JSON in `references/observation-format.md` - nothing else.

**A lens brief is data, not a hint.** Per this repo's own
[audit protocol](../../../../../.claude/rules/audit-protocol.md): give the lens the diff, the
changed-file list, the citable-line set, and the rule context - never a hypothesis about what is
wrong, a mention of what was just fixed, or a "verify that X" framing. Tainted context produces
false positives and misses what an independent read would have found.

**Probe capabilities before depending on them.** If Scout MCP tools, `gh`, or an issue-tracker
integration are present in the session, tell lenses to use them; otherwise the lens falls back to
`Grep`/`Glob` (for code and reference lookups) or a plain read-only lookup command named in the
repo profile (for tracker keys), and **says in its evidence which path it took**. Never let a
lens claim an index-backed answer it did not actually get. A claim about what code elsewhere in
the repo actually does should be delegated to a plain subagent dispatched for that one question,
rather than grepped inline - it keeps the lens's own context clean and gives a citable verdict.

**Pass the doc's own accountability sections.** If the changed document carries its own
`## Sources`, `## References`, or `## Changelog` section, read and pass those along - they are
what its claims are accountable to, and a claim asserted as sourced with no matching row in that
section is one of the highest-value findings available. The repo profile may name additional
accountability conventions.

**Verify each lens actually reported.** A lens can drift off-task and return prose, or answer a
different question entirely. Check every dispatch came back with parseable JSON in the expected
shape; treat a lens that did not as FAILED, re-dispatch it once with a tighter output contract,
and if it fails again record it in the report's coverage line. A silently-missing lens reads
exactly like a lens that found nothing.

## Step 4 - Validate mechanically (no model, no exceptions)

This is a separate gate from each lens's own `quality-gates.md` self-check (Step 3): that one
runs *inside* the lens before it emits anything; this one is the orchestrator re-checking every
surviving finding independently, and it is what actually enforces the citable-line contract - a
lens can misapply its own gate, this one cannot be talked out of dropping a bad citation.

Do this yourself, in code - not by asking an agent to be careful. Drop, and count:

- a required field missing (`theme`, `category`, `priority`, `confidence`,
  `location.file`, `location.line`, `observation`, `concern`, `evidence`)
- `location.file` not in the changed-file list
- `location.line` not in that file's citable-line set (**the single most common
  hallucination** - a lens that read the whole file cites *file* lines, not *diff* lines. On a
  large document this is near-certain on the first run; a zero drop count here means the gate is
  not running)
- `end_line` set and any line in `line..end_line` not citable
- the file is binary/generated/vendored/scratch per the Step 1 skip table
- `confidence` is MEDIUM or LOW with no `uncertainty_reason`
- a `suggestion.code` whose `replaces` text does not appear in the patch ->
  **strip the suggestion, keep the finding**

Then merge findings that share a `file:line` **and the same `category`** - those are true
duplicates. Only two categories are declared by more than one lens
(`unresolvable-reference-path` in `code`/`cross-refs`, `unconfirmed-outbound-write` in
`code`/`disclosure`), so cross-lens merging is deliberately rare; where it applies, keep the
highest-priority theme:

```text
disclosure > claims > consistency > code > placement > cross-refs > structure
```

and record the rest in `also_flagged_under`.

**Do not merge on `file:line` alone.** A single "line" is routinely a long markdown table row or
a dense code line carrying several independent defects - a stale count *and* a dead file pointer,
or a security issue *and* a style violation on the same line. Merging those on line number alone
silently deletes real findings. Co-located findings with different categories are both kept,
cross-linked through `related_to`. A leaked credential outranks a wrong count; a false *fact*
outranks an internal contradiction (a contradiction means one of two statements is wrong, a false
claim means one definitely is); structure loses every tie.

Report the drop count per lens in the output. A lens that keeps getting dropped is miscalibrated,
and that is worth knowing.

## Step 5 - Challenge (the false-positive filter)

Dispatch one subagent with the surviving findings and the **absolute paths of
`references/challenge-criteria.md` and `references/quality-gates.md`** - criterion 15 sends the
challenger to gate 8 for the tool-detection order, and a relative path resolves from nowhere in a
subagent. Batch by file overlap at ~100 KB and run batches in parallel.

The challenger's contract: **rejection requires evidence.** "I'm not sure" means keep. It uses
each finding's `uncertainty_reason` to know where to look, and returns
`{ accepted[], rejected[] }` where every rejection carries a stable `fp_decision` id. Replace each
accepted finding's `confidence` with the challenger's `verified_confidence` - it may have
*raised* it after verifying.

If the challenge pass fails entirely, present the validated findings and say the challenge did
not run.

## Step 6 - Report

Lead with findings. Do not replay the diff back as prose.

```text
## Review - <scope> (<N> files)

<one-line verdict>

### CRITICAL / HIGH / MEDIUM
<file>:<line> - <observation>
  <concern>
  <suggestion, if any>
  (also flagged by: ...)   (confidence: MEDIUM - <uncertainty_reason>)

<details><summary>LOW (n)</summary> ... </details>

### Coverage
Lenses: <which ran>  ·  Dropped by validation: <n>  ·  Rejected by challenge: <n>
Skipped files: <binary/generated/scratch>
Rule sources: <files discovered>  ·  Profile: <found | not found>
```

Zero findings is a real and frequent outcome - say so plainly and stop. Never pad. Never approve
or bless the change; report and let the human decide. Findings go **in-chat only** - do not write
a findings file.

## Examples

Review everything on this branch, including the working tree (the default):

```text
/review-changes
```

Review only what is staged, right before a commit:

```text
/review-changes staged
```

Review a specific set of files regardless of git status:

```text
/review-changes plugins/boss-dev/agent-harness/skills/harness-doctor/SKILL.md README.md
```

Sweep a whole file for stale content that predates the branch (opt-in, noisier):

```text
/review-changes full docs/architecture.md
```

## Troubleshooting

**"cannot resolve a base branch"** - no remote is configured and none of `main`/`master`/
`develop`/`trunk` exist locally. Pass an explicit base or path list instead of relying on
detection.

**Every finding on a large file gets dropped by Step 4** - this is the gate working, not failing.
A lens that read the whole file with `Read` instead of the annotated patch cites file line
numbers, not diff line numbers; re-dispatch it with an explicit reminder to cite only `[N]` from
the patch it was given.

**A lens returns prose instead of JSON** - it drifted off-task, most often because it was not
given the absolute paths to `quality-gates.md`, `observation-format.md`, and `repo-profile.md`
and could not resolve the bare filenames it cites internally. Re-dispatch with those paths
spelled out.

**The review is unexpectedly quiet in an unfamiliar repo** - this is correct. Without a discovered
`CLAUDE.md`/`AGENTS.md`/`.cursor/rules` or a `.claude/review-changes.md` profile, the `placement`
lens in particular has nothing to cite and reports nothing. A quiet review in a repo with no
conventions is the pass condition, not a bug - see
[references/repo-profile.md](references/repo-profile.md) to add one.

**Untracked files are missing from the review** - confirm they are not excluded by `.gitignore`;
an ignored file is intentionally out of scope unless it is force-added and tracked.

## When to run it

Before the commit that ends a unit of work, and before anything that publishes further than this
working tree - opening a pull request, publishing a document, or syncing to an external tracker.

It complements, not replaces, whatever the repo already enforces mechanically. Before reporting a
finding, check what the target repo's own tooling already owns, in order of authority:

1. `.pre-commit-config.yaml` / `lefthook.yml` - what blocks a commit
2. `.github/workflows/*` (or the repo's CI config) - what blocks a merge
3. tool config: `pyproject.toml`, `eslint.config.*`/`.eslintrc*`, `biome.json`, `.prettierrc*`,
   `rustfmt.toml`, `.golangci.yml`, `.rubocop.yml`, `.editorconfig`, a markdown-lint config
4. `Makefile` / `justfile` targets

Whatever those already own is not a finding here. Formatting, import order, line length, and
markdown style are never findings regardless of what the repo's tooling covers.

Security-vulnerability review is a related but separate concern with its own severity model - see
[`boss-security-review`](../boss-security-review/SKILL.md). This skill's `disclosure` lens covers
credential exposure and prompt-injection surface in the diff itself; a full vulnerability sweep
of the codebase is `boss-security-review`'s job, not this one's.

## Related skills

- [`boss-security-review`](../boss-security-review/SKILL.md) - the companion for a dedicated
  security-vulnerability pass with its own severity model
  ([references/severity-model.md](../boss-security-review/references/severity-model.md)) and
  subagent fan-out contract
  ([references/fanout.md](../boss-security-review/references/fanout.md)); this skill's severity
  vocabulary (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`) is chosen to be compatible with it.
- [`fetch-diff`](../fetch-diff/SKILL.md) - the equivalent annotated-diff idea for a **remote** PR
  URL rather than the local working tree; use it when the review target is a GitHub PR number
  instead of an in-progress branch.
- Once findings are addressed and it is time to open the PR, see
  [`commit-push-pr`](../../commands/commit-push-pr.md).

## Reference Files

- [`references/observation-format.md`](references/observation-format.md) - consult before
  dispatching any lens: the finding JSON, field by field, and the two-axis
  `priority`/`confidence` contract.
- [`references/quality-gates.md`](references/quality-gates.md) - consult when a lens is drafting
  a finding: the eight checks it must pass before reporting, including what is already someone
  else's job (gate 8) and how to check that mechanically.
- [`references/challenge-criteria.md`](references/challenge-criteria.md) - consult in Step 5: the
  false-positive taxonomy with stable ids, so a rejection can be justified and compared across
  runs.
- [`references/repo-profile.md`](references/repo-profile.md) - consult in Step 2: how rules are
  discovered generically, and the optional `.claude/review-changes.md` contract for sharpening
  discovery with repo-specific knowledge.
- One file per lens under `references/lenses` - `claims.md`, `consistency.md`, `structure.md`,
  `cross-refs.md`, `placement.md`, `disclosure.md`, `code.md` - each with that lens's domain,
  categories, evidence bar, and what NOT to report.
