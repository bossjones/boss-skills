---
name: fetch-diff
description: Fetch a GitHub PR diff with old/new line numbers and auto-generated-file masking for code review. Use when you need a pull request's diff annotated with line numbers to place inline review comments, or want the diff filtered to specific file globs.
allowed-tools:
  - Bash(uv run:*)
---

# Fetch PR Diff

Fetches a pull request diff and adds line numbers for easier review-comment
placement. Auto-generated files (lock files, protobuf-generated Java) are shown
with masked diffs so review focuses on hand-written changes.

## Usage

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" <pr_url> [--files <pattern> ...]
```

The script is a self-contained PEP 723 script — `uv run` resolves its
dependencies on demand; no install step is needed.

## Examples

```bash
# Fetch the full diff
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" https://github.com/owner/repo/pull/123

# Fetch only Python files
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" https://github.com/owner/repo/pull/123 --files '*.py'

# Fetch only frontend files
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" https://github.com/owner/repo/pull/123 --files 'src/server/js/*'

# Multiple patterns
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" https://github.com/owner/repo/pull/123 --files '*.py' '*.ts'
```

The GitHub token is auto-detected from the `GH_TOKEN` environment variable or
`gh auth token`.

## Inputs and outputs

`scripts/fetch_diff.py` takes:

- **`pr_url`** (positional, required) — a GitHub PR URL of the form
  `https://github.com/<owner>/<repo>/pull/<number>`. Sub-paths like `/files`
  are not accepted; use the bare `/pull/<n>` form.
- **`--files <pattern> ...`** (optional) — one or more `fnmatch` globs matched
  against each file's new path. Files matching any pattern are kept; the rest
  are dropped. No match yields an empty diff (not an error).
- **`GH_TOKEN`** (env) — the token used to call the GitHub API. If unset, the
  script falls back to `gh auth token`; if that also fails it exits with an
  error.

It prints the PR's unified diff to **stdout**, reorganized per file: each file
keeps its `diff --git` header, then either line-annotated hunks (see
[Line Annotation](#line-annotation)) or a one-line mask message for
auto-generated and deleted files. A single diagnostic line goes to **stderr**
when a stacked-PR incremental diff is detected. See
[`references/output-format.md`](references/output-format.md) for the full
schema.

## Output Example

**Regular file:**

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

**Deleted file (masked):**

```text
diff --git a/path/to/removed.py b/dev/null
index abc123..0000000 100644
--- a/path/to/removed.py
+++ /dev/null
[Deleted file - diff masked]
```

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
