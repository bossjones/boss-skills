# GraphQL Query and Output Schema

This skill queries GitHub's GraphQL API for a pull request's review threads,
keeps only the ones that are still open, and emits them as JSON grouped by file.
This document explains why GraphQL is required, the shape of the query, and the
exact output schema the script produces.

## Why GraphQL (and not REST)

The GitHub REST API exposes individual review comments
(`GET /repos/{owner}/{repo}/pulls/{n}/comments`), but a REST comment carries no
field telling you whether the *thread* it belongs to has been resolved. "Resolved"
is a property of a review thread, and that concept is only surfaced through the
GraphQL API's `reviewThreads` connection and its `isResolved` boolean.

So to answer "which review feedback is still open?" you must:

1. Walk `pullRequest.reviewThreads`, and
2. Filter on each thread's `isResolved` flag.

REST alone cannot make the resolved/unresolved distinction, which is the entire
point of this skill.

## Query shape

The script issues a single GraphQL query, parameterized by the PR's owner, repo,
and number. The traversal is:

```text
repository(owner, name)
  └─ pullRequest(number)
       └─ reviewThreads(first: 100)
            └─ nodes
                 ├─ id           # the thread node id (becomes thread_id)
                 ├─ isResolved   # the resolved/unresolved filter
                 └─ comments(first: 100)
                      └─ nodes
                           ├─ id
                           ├─ databaseId   # numeric id used in output
                           ├─ body
                           ├─ path         # file the thread is anchored to
                           ├─ line
                           ├─ startLine    # set for multi-line comments
                           ├─ diffHunk     # surrounding diff context
                           ├─ author { login }
                           ├─ createdAt
                           └─ updatedAt
```

Notes on the fields:

- `path`, `line`, `startLine`, and `diffHunk` are read from the **first** comment
  in each thread; they describe where the thread is anchored in the diff. The
  skill treats those as thread-level metadata.
- `startLine` is `null` for single-line comments and populated for multi-line
  selections.
- `author` can be `null` (e.g. a deleted account); the script falls back to the
  literal string `"unknown"` in that case.
- The query fetches the first 100 threads and the first 100 comments per thread.
  See `troubleshooting.md` for what happens on PRs that exceed those limits.

## Filtering rules

A thread is **kept** only when all of the following hold:

- `isResolved` is `false` — resolved threads are skipped entirely.
- The thread has at least one comment.
- The first comment has a non-null `path` (threads not anchored to a file are
  skipped).

`total` counts every comment across the kept threads, not the number of threads.

## Output JSON schema

The script prints a single JSON object to stdout:

```text
{
  "total": <int>,                       # count of comments across kept threads
  "by_file": {
    "<path>": [                         # file path → list of open threads
      {
        "thread_id": "<string>",        # GraphQL thread node id
        "line": <int | null>,           # anchor line (from first comment)
        "startLine": <int | null>,      # multi-line start, else null
        "diffHunk": "<string | null>",  # diff context (from first comment)
        "comments": [
          {
            "id": <int>,                # databaseId of the comment
            "body": "<string>",         # comment text (markdown)
            "author": "<string>",       # login, or "unknown"
            "createdAt": "<ISO-8601>"   # e.g. 2026-05-17T00:53:20Z
          }
        ]
      }
    ]
  }
}
```

Field-by-field:

| Field | Type | Source |
| --- | --- | --- |
| `total` | int | running count of kept comments |
| `by_file` | object | maps each file path to its open threads |
| `by_file[path][].thread_id` | string | thread `id` from GraphQL |
| `by_file[path][].line` | int \| null | `line` of the first comment |
| `by_file[path][].startLine` | int \| null | `startLine` of the first comment |
| `by_file[path][].diffHunk` | string \| null | `diffHunk` of the first comment |
| `by_file[path][].comments[].id` | int | `databaseId` of the comment |
| `by_file[path][].comments[].body` | string | comment body |
| `by_file[path][].comments[].author` | string | author `login`, else `"unknown"` |
| `by_file[path][].comments[].createdAt` | string | ISO-8601 timestamp |

When there are no open threads, `total` is `0` and `by_file` is an empty object
(`{}`). Multiple threads on the same file appear as multiple entries in that
file's list, ordered as GitHub returns them.
