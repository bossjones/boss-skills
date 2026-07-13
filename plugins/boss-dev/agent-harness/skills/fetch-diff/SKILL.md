---
name: fetch-diff
description: This skill should be used when a GitHub pull request diff, or a local branch diff against its merge-base, is needed with old/new line numbers annotated for placing inline review comments. Triggers on "get the diff for PR 123", "review my branch before I open a PR", "diff this branch against main", "show me what changed in this PR", or when a diff must be filtered to specific file globs. Generated files (lock files, bundles) are masked; database migrations never are.
allowed-tools:
  - Bash(uv run:*)
  - Bash(git rev-parse:*)
  - Bash(gh auth status:*)
---

# Fetch Diff

Fetches a diff and adds line numbers for easier review-comment placement.
Generated files (lock files, minified bundles, sourcemaps, `@generated`-marked
sources) are shown with masked diffs so review focuses on hand-written changes.
**Database migrations are never masked** — a bad migration can destroy
production data, so it must always reach a reviewer.

Two caveats worth knowing before trusting the mask:

- The `@generated` check **reads the local working tree**, so it only applies
  inside a checkout of the repo under review. Fetching an upstream PR from an
  unrelated directory silently skips it (lock-file and suffix matching still
  work — those are name-based).
- The mask message is emitted **at the first hunk**. A generated file changed by
  a rename or a mode-only edit has no hunks, so it carries no mask marker at all.
  Do not assume the marker is always present.

Two sources, one annotated format:

- **PR mode** — a GitHub pull request, via the API.
- **Local mode** — the working branch, diffed against its merge-base with a ref.

Both go through the same annotation pass, so a `file:line` anchor means the same
thing regardless of source.

## Usage

```bash
# PR mode
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" <pr_url> [--files <pattern> ...]

# Local mode
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" --base <ref> [--files <pattern> ...]
```

Exactly one of `<pr_url>` or `--base` is required. The script is a self-contained
PEP 723 script — `uv run` resolves its dependencies on demand; no install step is
needed.

## Examples

```bash
# Fetch the full PR diff
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" https://github.com/owner/repo/pull/123

# Fetch only Python files
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" https://github.com/owner/repo/pull/123 --files '*.py'

# Multiple patterns
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" https://github.com/owner/repo/pull/123 --files '*.py' '*.ts'

# Review the current branch before opening a PR
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" --base main

# Local mode, Python files only
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" --base develop --files '*.py'
```

The GitHub token is auto-detected from the `GH_TOKEN` environment variable or
`gh auth token`. Local mode needs no token — it only shells out to `git`.

## Inputs and outputs

`scripts/fetch_diff.py` takes:

- **`pr_url`** (positional, optional) — a GitHub PR URL of the form
  `https://github.com/<owner>/<repo>/pull/<number>`. Sub-paths like `/files`
  are not accepted; use the bare `/pull/<n>` form.
- **`--base <ref>`** (optional) — local mode. Runs
  `git diff --merge-base <ref> HEAD`, so the diff shows only what this branch
  changed, not what it is merely behind on (the local equivalent of a PR's
  three-dot diff). Mutually exclusive with `pr_url`; one of the two is required.
- **`--files <pattern> ...`** (optional) — one or more `fnmatch` globs matched
  against each file's new path. Files matching any pattern are kept; the rest
  are dropped. No match yields an empty diff (not an error).
- **`GH_TOKEN`** (env) — the token used to call the GitHub API in PR mode. If
  unset, the script falls back to `gh auth token`; if that also fails it exits
  with an error. Unused in local mode.

It prints the unified diff to **stdout**, reorganized per file: each file keeps
its `diff --git` header, then either line-annotated hunks (see
[Line Annotation](#line-annotation)) or a one-line mask message for generated and
deleted files. A single diagnostic line goes to **stderr** when a stacked-PR
incremental diff is detected.

Errors also go to stderr and always pair with a **non-zero exit code**. Check the
exit status — an auth failure otherwise looks exactly like a PR that changed
nothing. See [`references/output-format.md`](references/output-format.md) for the
full schema.

## Output Example

**Regular file** (columns are 5-wide and right-aligned — this is literal output):

```text
diff --git a/path/to/file.py b/path/to/file.py
index abc123..def456 100644
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -10,7 +10,7 @@
   10    10 |  import os
   11    11 |  import sys
   12    12 |  from typing import Optional
   13       | -from old_module import OldClass
         14 | +from new_module import NewClass
   14    15 |
   15    16 |  def process_data(input_file: str) -> dict:
```

**Auto-generated file (masked):**

```text
diff --git a/uv.lock b/uv.lock
index abc123..def456 100644
--- a/uv.lock
+++ b/uv.lock
[Auto-generated file - diff masked]
```

**Deleted file (masked)** — git repeats the real path in the `diff --git` header;
`/dev/null` appears only on the `+++` line, and the `deleted file mode` line is
what triggers the mask:

```text
diff --git a/path/to/removed.py b/path/to/removed.py
deleted file mode 100644
index abc123..0000000
--- a/path/to/removed.py
+++ /dev/null
[Deleted file - diff masked]
```

**Migration (never masked)** — see
[`references/output-format.md`](references/output-format.md#migrations-are-never-masked).

## Line Annotation

Each line is annotated as `old_line new_line | <marker> content`:

- `-` marker (left number only) -> deleted line; comment with `side=LEFT`, `line=old_line`
- `+` marker (right number only) -> added line; comment with `side=RIGHT`, `line=new_line`
- No marker (both numbers) -> unchanged line; comment with `side=RIGHT`, `line=new_line`

## Reference Files

- [`references/output-format.md`](references/output-format.md) — consult when
  parsing the annotated diff: the column schema, marker meanings, how masked and
  deleted files render, and how stacked-PR incremental diffs are signaled.
- [`references/troubleshooting.md`](references/troubleshooting.md) — consult when
  the fetch fails or surprises you: auth errors, PR-not-found / private repos,
  large diffs, `--files` glob behavior and no-match output, and line-anchoring
  pitfalls when the result feeds `add-review-comment`.

## Related skills

This skill is the first step of the PR-review family in `agent-harness`:

1. **fetch-diff** (this skill) — get the diff annotated with old/new line numbers.
2. [`add-review-comment`](../add-review-comment/SKILL.md) — post an inline
   comment using the `side`/`line` anchors this skill produces.
3. [`pr-review`](../pr-review/SKILL.md) — review a whole PR end to end.
4. [`fetch-unresolved-comments`](../fetch-unresolved-comments/SKILL.md) — pull
   back the review threads that still need a response.
