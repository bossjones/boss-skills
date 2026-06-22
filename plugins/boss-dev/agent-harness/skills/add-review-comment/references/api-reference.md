# GitHub Review Comment API Reference

This skill posts one inline review comment by calling the GitHub REST API
through the `gh` CLI. This file documents the endpoint, its parameters, and the
anchor rules so you can construct a correct request without guessing.

## Endpoint

```text
POST /repos/{owner}/{repo}/pulls/{pull_number}/comments
```

Invoked via `gh api` as:

```bash
gh api repos/<owner>/<repo>/pulls/<pr_number>/comments [params] --jq '.html_url'
```

A successful call creates a standalone review comment anchored to a line in the
PR diff and returns the comment object as JSON. `--jq '.html_url'` extracts the
permalink to the new comment so the caller gets back a single URL.

Note: this endpoint creates a *single inline comment* immediately. It is not the
"pending review" batch endpoint (`POST .../reviews`). Each call posts one comment
right away.

## Parameters

`gh api` flags map to the JSON body. Use `-f` for string fields and `-F` for
numeric (or otherwise typed) fields so integers are not quoted.

| Parameter     | Flag | Required        | Meaning |
|---------------|------|-----------------|---------|
| `body`        | `-f` | Yes             | Comment text (Markdown). End with the `🤖 Generated with Claude` footer on its own line. |
| `path`        | `-f` | Yes             | File path relative to the repo root. Must have a hunk in the PR diff. |
| `commit_id`   | `-f` | Yes             | SHA of the PR head commit the comment is anchored to. Resolve inline (see below). |
| `line`        | `-F` | Yes             | Line number in the file to anchor to. For a range, this is the **last** line. |
| `side`        | `-f` | Recommended     | `RIGHT` (post-change file) or `LEFT` (pre-change file). Defaults to `RIGHT`. |
| `start_line`  | `-F` | Multi-line only | First line of a multi-line range. Must be `<= line`. |
| `start_side`  | `-f` | Multi-line only | Side of `start_line` (`RIGHT` or `LEFT`). |

### Resolving `commit_id`

The anchor must reference the current head commit of the PR. Resolve it inline so
it is never stale:

```bash
commit_id="$(gh pr view <pr_number> --repo <owner>/<repo> --json headRefOid -q .headRefOid)"
```

## Single-line vs multi-line anchors

- **Single-line** — supply `path`, `line`, and `side`. The comment attaches to
  exactly that line.
- **Multi-line** — additionally supply `start_line` and `start_side`. The range
  runs from `start_line` to `line` inclusive, so `start_line` must be the smaller
  number. Mixing sides (a `LEFT` start with a `RIGHT` end) is not supported for a
  single range — keep both sides the same.

### Choosing `side`

- `RIGHT` — added or unchanged/context lines as they appear in the post-merge
  file. This is the common case for comments on new or modified code.
- `LEFT` — deleted lines as they appeared before the change. Use this only when
  commenting on a line that was removed.

The `line` value is the line number *within the chosen side's file*, not a
diff-relative offset. Get these numbers from the `fetch-diff` skill, which
annotates the diff with real file line numbers.

## Suggestion blocks (one-click fixes)

To offer a change the maintainer can apply with one click, embed a fenced
`suggestion` block in `body`. GitHub renders it as an "Apply suggestion" button.

````text
```suggestion
<the exact replacement text for the anchored line(s)>
```
````

Rules that make a suggestion apply cleanly:

- The block's lines replace exactly the anchored line range. For a single-line
  comment, provide one line; for a multi-line range, provide the full
  replacement for that range.
- Preserve the original indentation exactly — the suggestion is substituted
  verbatim, so a wrong indent produces a broken apply.
- Only one suggestion block per comment applies as a button; put explanatory
  prose before or after it.
