# Troubleshooting

Common failure modes when fetching a diff, and how to recover. The skill has two
modes; the first section applies to both, then PR-mode and local-mode failures are
covered separately.

## Choosing a mode

Exactly one of `<pr_url>` or `--base <ref>` is required.

- Passing **both**, or **neither**, exits non-zero with
  `provide exactly one of <pr_url> or --base REF`. There is no default mode —
  reviewing the wrong source silently would be worse than an error.

## Local mode (`--base`)

Local mode shells out to `git diff --merge-base <ref> HEAD`. It needs no token, but
it does need a git repository with a shared history.

- **Unknown or typo'd ref** — exits with
  `git diff --merge-base <ref> HEAD failed: ...`. Check the ref exists locally
  (`git rev-parse <ref>`); a remote-only branch may need `git fetch` first, or an
  explicit `origin/<ref>`.
- **Not inside a git repository** — git's own error is surfaced. Run from within the
  checkout, or pass the repo as the working directory.
- **No common ancestor** — if the branch and `<ref>` have unrelated histories there
  is no merge-base and git fails. This usually means the wrong `<ref>`, or a repo
  grafted from an unrelated history.
- **Detached HEAD** — works fine; `HEAD` is just the current commit. The diff is
  still computed against the merge-base with `<ref>`.
- **Uncommitted changes are not reviewed.** The diff is `HEAD` versus the
  merge-base, so anything unstaged or staged-but-uncommitted is invisible. Commit
  first if you want it reviewed.

## Authentication (PR mode only)

The script needs a GitHub token. It looks at `GH_TOKEN` first, then falls back
to running `gh auth token`. If neither is available it prints
`Error: GH_TOKEN not found (set env var or install gh CLI)` and exits non-zero.

- **No token at all** — set `GH_TOKEN` to a personal access token, or log in
  with `gh auth login` so `gh auth token` succeeds.
- **`gh` installed but not logged in** — `gh auth token` fails, so the script
  treats it as "no token". Run `gh auth login` (or `gh auth status` to check).
- **Token lacks scope** — a token that cannot read the repo will surface as an
  HTTP error from the API rather than the "not found" message above. For
  private repos the token needs `repo` scope.

## PR not found / wrong URL

The URL must match `https://github.com/<owner>/<repo>/pull/<number>`.

- A URL that does not match this shape raises `Invalid PR URL: <url>`. The
  `/files`, `/commits`, or `/checks` sub-paths are *not* accepted — strip them
  back to the bare `/pull/<n>` form.
- A well-formed URL pointing at a PR that does not exist (typo'd number, wrong
  repo, deleted PR) returns an HTTP 404 from the API and raises an error. Double
  check owner, repo, and number.

## Private repositories

A private repo behaves like "not found" unless the token can see it. If a URL
is correct but you get a 404, confirm the token's account has access to the repo
and that the token carries `repo` scope (fine-grained tokens need the specific
repository selected with read access to contents and pull requests).

## Large diffs

Very large PRs produce a lot of output. There is no built-in pagination or
truncation, so the whole annotated diff is printed at once — which can be slow
to scan and expensive to feed downstream.

- Scope the fetch with `--files` to only the paths you intend to review.
- Remember that the usual bulk offenders are already masked — lock files, minified
  bundles (`.min.js` / `.min.css`), sourcemaps (`.map`), and any file whose first
  line carries an `@generated` marker — so machine-generated churn does not dominate
  the output. See
  [`output-format.md`](output-format.md#masked-files) for the full rule set.
- Migrations are deliberately **never** masked, so a migration-heavy PR stays large
  on purpose.

## `--files` glob behavior

`--files` accepts one or more shell-style globs, matched against the file's
*new* path with `fnmatch`:

- `fnmatch` is path-unaware: `*` matches across `/`, so `*.py` matches
  `src/server/app.py`, and `src/server/*` matches `src/server/js/main.ts`.
- Patterns are matched against the path exactly as it appears in the diff
  header (no leading `a/` or `b/`).
- Multiple patterns are OR-ed: a file is included if it matches any pattern.
- **No matches** is not an error — the script simply emits an empty diff. If you
  get empty output, re-check the glob against the actual paths in the PR (try
  the full diff first without `--files`).

## Line-number anchoring pitfalls

The annotated line numbers are meant to be handed to `add-review-comment`. A few
things to keep in mind:

- Use the column that matches the marker: removed lines anchor on the **old**
  number with `side=LEFT`; added and context lines anchor on the **new** number
  with `side=RIGHT`. Mixing these up posts the comment on the wrong line.
- Masked files (auto-generated or deleted) have no per-line annotation, so you
  cannot anchor an inline comment inside them from this output.
- If you fetched with `--files`, the line numbers are still the true file line
  numbers (filtering removes whole files, it does not renumber survivors), so
  they remain valid anchors.
- For a stacked PR the diff is the incremental compare between base and head
  SHAs; line numbers are correct for the head revision, which is what the review
  API expects.
