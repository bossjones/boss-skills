# Troubleshooting

Common failure modes when fetching unresolved review comments, and how to read
or work around them.

## Authentication errors

The script discovers a token in this order:

1. The `GH_TOKEN` environment variable.
2. `gh auth token` (the GitHub CLI's stored credential).

If neither is available it prints
`Error: GH_TOKEN not found (set env var or install gh CLI)` to stderr and exits
with a non-zero status. To fix:

- Export a token: `export GH_TOKEN=<your-token>`, or
- Authenticate the CLI once with `gh auth login` so `gh auth token` succeeds.

If a token is present but invalid or expired, GitHub responds with HTTP 401 and
the request raises an error rather than returning data. Re-issue the token or run
`gh auth refresh`.

## PR not found

The PR URL is parsed against the pattern
`https://github.com/<owner>/<repo>/pull/<number>`. A URL that doesn't match
(e.g. a commit URL, an issue URL, or a shortened link) raises
`Invalid PR URL: <url>` before any network call. Pass the canonical PR URL.

If the URL parses but the PR doesn't exist (wrong number, wrong repo) GitHub's
GraphQL response will contain a `null` pull request, which surfaces as an error
when the result is unpacked. Double-check the owner, repo, and number.

## Permissions on private repositories

GraphQL only returns review threads the token's account can see. For a private
repo, the token must belong to an account with read access to that repo. With an
insufficient token you'll typically see an empty or partial response (GitHub
hides what you can't read rather than erroring loudly). If a PR you know has open
threads comes back empty, suspect a permissions/visibility problem first.

## Empty result (no open threads)

A successful run on a PR with no unresolved feedback prints
`{"total": 0, "by_file": {}}`. This is **not** an error — it means every review
thread is resolved (or the PR has no review threads at all). It's the expected
"all clear" signal after addressing feedback.

## Resolved vs. unresolved

The skill deliberately excludes threads whose `isResolved` flag is `true`. Once a
reviewer (or the resolve workflow) marks a thread resolved, it disappears from
this output. That's the design: the skill answers "what still needs attention?",
not "what was ever said?". If you need the full history, including resolved
threads, this skill is the wrong tool — query the review comments directly or
drop the `isResolved` filter in a one-off query.

A thread can also be filtered out even when unresolved if its first comment has
no `path` (it isn't anchored to a file in the diff). Such threads are uncommon
but will be absent from `by_file`.

## Pagination on large PRs

The query requests the first 100 review threads and the first 100 comments per
thread. PRs with more than 100 threads, or a single thread with more than 100
comments, will be **silently truncated** — the extra nodes simply won't appear.
This is rare for typical reviews but worth knowing for very long-running PRs. If
you hit it, the query needs cursor-based pagination (following the connection's
`pageInfo.endCursor`) rather than a single fixed-size page.

## Rate limiting

GraphQL requests count against GitHub's GraphQL rate limit, which is computed
from query complexity rather than a flat request count. A single call from this
skill is cheap, so you're unlikely to be limited by normal interactive use.
Tight automation loops that re-fetch the same PR repeatedly can still hit the
limit; if you see HTTP 403 with a rate-limit message, back off and retry after
the window resets (the response headers report when that is).
