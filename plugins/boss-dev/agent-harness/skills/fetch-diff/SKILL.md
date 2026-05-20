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
