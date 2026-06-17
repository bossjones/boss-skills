# Enhance Claude workflows + add a security-review workflow

## Context

`boss-skills` had two Claude-powered GitHub workflows — `.github/workflows/claude.yml`
(interactive `@claude` mentions) and `.github/workflows/claude-code-review.yml` (automated
PR review via the `code-review` plugin) — but **no security or dependency scanning** (no
CodeQL, Dependabot, SAST, or CVE audit). The repo manages Python deps with `uv` and commits
`uv.lock`, making it a natural fit for the new (preview) `uv audit` command, and Anthropic
publishes a dedicated `claude-code-security-review` action for AI semantic scanning of PR
diffs.

This change set:

1. **Tunes up** the two existing workflows: per-PR **concurrency** and a **refreshed model
   option** (Opus 4.7 → Opus 4.8).
2. **Adds** `.github/workflows/security-review.yml` with two jobs — a non-blocking `uv audit`
   dependency scan (results posted as a sticky PR comment) and the
   `anthropics/claude-code-security-review` AI scan of the PR diff.

## Research findings that shaped the design

- **`claude-code-action` is at v1** (latest tag `v1.0.150`). `prompt` present ⇒ automation
  mode; absent ⇒ interactive `@claude` mode. `claude_args` carries `--model` / `--allowedTools`.
  The repo already uses v1 correctly — no migration needed.
- **`uv audit` is preview with no machine-readable output** (verified against uv 0.11.14 via
  `uv audit --help`): no `--json`, `--sarif`, or `--output-format`. It audits the project via
  `uv.lock`, prints human-readable text, exits non-zero on findings, and supports
  `--ignore <ID>` / `--ignore-until-fixed <ID>`, `--color`, `--no-dev`, `--frozen`. ⇒ Gating
  is by exit code only, so the job is **report-only** (`continue-on-error: true`).
- **`claude-code-security-review`** key inputs: `claude-api-key` (required), `comment-pr`
  (default `true`), `upload-results` (default `true`), `exclude-directories`,
  `claudecode-timeout` (default `20`), `claude-model`, `run-every-commit` (default `false`),
  `false-positive-filtering-instructions`, `custom-security-scan-instructions`. On
  `pull_request` it scans **only the diff**. README checks out
  `ref: ${{ github.event.pull_request.head.sha || github.sha }}` with `fetch-depth: 2`, perms
  `contents: read` + `pull-requests: write`.
- **Hooks caveat**: this repo's `.claude/settings.json` wires lifecycle hooks to `uv run ...`.
  Both existing Claude workflows install `uv` for exactly this reason. The security-scan job
  also runs `claude` against this repo, so it **installs `uv` too** to avoid `uv: not found`.
- **Secret reuse**: the security action's input is `claude-api-key`; the secret name is
  arbitrary. We reuse the already-configured `secrets.ANTHROPIC_API_KEY` — no new secret.

## Design decisions

| Decision | Choice | Why |
| --- | --- | --- |
| Concurrency — review workflow | `cancel-in-progress: true` | A new push supersedes the in-flight review; the old run is wasted spend. |
| Concurrency — interactive workflow | `cancel-in-progress: false` (serialize) | Cancelling a half-finished `@claude` task (editing files / writing a comment) is destructive; serialize per issue/PR instead. |
| uv audit gating | Report-only (`continue-on-error: true`) | Preview-stage tool shouldn't gate merges. Flip to blocking later by dropping the flag. |
| uv audit reporting | Job summary **and** sticky PR comment | Comment is keyed by a hidden `<!-- uv-audit-report -->` marker and updated via `gh pr comment --edit-last`, so re-runs refresh one comment instead of stacking. Uses implicit `${{ github.token }}`; no third-party action. |
| Security action pinning | Pinned to commit SHA, not `@main` | Supply-chain safety. Pinned to `0c6a49f1…` (main @ 2026-06-17). |
| Draft skip / job timeout | Not applied | Opted out; security jobs run on the same PR event types as the existing review workflow. |

## Changes

### 1. `.github/workflows/claude-code-review.yml`

Added a top-level `concurrency:` block (between `on:` and `jobs:`):

```yaml
concurrency:
  group: claude-review-${{ github.event.pull_request.number }}
  cancel-in-progress: true
```

Refreshed the commented model alternative:

```diff
- # claude_args: '--model claude-opus-4-7'   # Opus 4.7 — stronger reasoning
+ # claude_args: '--model claude-opus-4-8'   # Opus 4.8 — stronger reasoning
```

The active `--model claude-sonnet-4-6` (cheap default) is unchanged.

### 2. `.github/workflows/claude.yml`

Added a top-level `concurrency:` block:

```yaml
concurrency:
  group: claude-${{ github.event.issue.number || github.event.pull_request.number }}
  cancel-in-progress: false
```

### 3. `.github/workflows/security-review.yml` (new)

Two jobs on `pull_request`:

- **`dependency-audit`** — installs `uv` (setup-uv@v5, pinned `0.11.15`, Python 3.13), runs
  `uv audit --color never` (report-only, `continue-on-error: true`), writes output to the job
  summary, and posts/updates a sticky PR comment with the result and a status line.
- **`claude-security-scan`** — checks out the PR head (`fetch-depth: 2`), installs `uv` (for
  the settings.json hooks), and runs `anthropics/claude-code-security-review` pinned to a SHA
  with `comment-pr: true` and `claude-api-key: ${{ secrets.ANTHROPIC_API_KEY }}`.

See the file for the full YAML.

## Validation

```bash
# YAML validity
uv run python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]; print('yaml ok')"

# actionlint (preferred)
actionlint .github/workflows/claude.yml .github/workflows/claude-code-review.yml .github/workflows/security-review.yml

# uv audit runs against the lockfile (non-zero exit = findings; report-only tolerates it)
uv audit || echo "exit $?"

# spot-check the edits
grep -n "claude-opus-4-8" .github/workflows/claude-code-review.yml
grep -rn "concurrency:" .github/workflows/claude*.yml .github/workflows/security-review.yml
```

## Follow-ups / notes

- Make `uv audit` blocking later by removing `continue-on-error: true`; use `--ignore <ID>`
  for accepted advisories.
- `claude-security-scan` and the existing `claude-code-review` both comment on PRs — expected
  per scope. Scope the security action with `exclude-directories` /
  `custom-security-scan-instructions` if it gets chatty.
- Re-pin the security action SHA when bumping; resolve via
  `gh api repos/anthropics/claude-code-security-review/commits/main --jq '.sha'`.
