# Passing long or multi-line review bodies safely

Long review/comment bodies tempt the author to draft the markdown into a scratch file and reference
it with an at-sign. The **wrong** way silently posts the file path as text.

## The trap (never do this)

`gh` posts the literal string `@/tmp/body.md`, not its contents, in both of these:

````bash
# WRONG: -f is a RAW field; @ is not expanded. Posts "@/tmp/body.md" verbatim.
gh api repos/:owner/:repo/pulls/<PR_NUMBER>/reviews/<REVIEW_ID>/events \
  -X POST -f event=COMMENT -f body="@/tmp/body.md"

# WRONG: gh pr review --body never reads files either.
gh pr review <PR_NUMBER> --body "@/tmp/body.md"
````

This is the exact bug that produced broken literal-path comments on real PRs. Use one of the three
correct forms below instead.

## Preferred: build a JSON payload and `--input`

Quoting-proof for any body, single- or multi-line. Construct the JSON with `jq` so the body is
escaped correctly, then pipe it to `gh api --input -`:

````bash
# Submit a review event with a multi-line body
jq -n --arg body "$REVIEW_BODY" '{event: "COMMENT", body: $body}' \
  | gh api repos/:owner/:repo/pulls/<PR_NUMBER>/reviews/<REVIEW_ID>/events -X POST --input -

# Create a pending review with batched inline comments
jq -n --arg sha "$COMMIT_SHA" --arg b1 "$COMMENT_1_BODY" '
  {
    commit_id: $sha,
    comments: [
      { path: "src/auth.ts", line: 20, side: "RIGHT", body: $b1 }
    ]
  }' \
  | gh api repos/:owner/:repo/pulls/<PR_NUMBER>/reviews -X POST --input - --jq '{id, state}'
````

`--input <file>` reads from a file; `--input -` reads the JSON from stdin. With `--input`, `gh` sends
the body as-is — no shell-quoting and no at-sign ambiguity.

## Field form: `-F field=@file`

If individual fields are required, only `-F/--field` expands an at-sign file reference (and `@-` for
stdin). `-f/--raw-field` never does:

````bash
# Reads the file contents into the body field
gh api repos/:owner/:repo/pulls/<PR_NUMBER>/reviews/<REVIEW_ID>/events \
  -X POST -f event=COMMENT -F 'body=@/tmp/body.md'
````

## `gh pr review` form: `--body-file`

The `gh pr review` porcelain reads files only through `--body-file`, not `--body`:

````bash
gh pr review <PR_NUMBER> --comment --body-file /tmp/body.md
````
