---
description: Debug failed GitHub Actions CI runs — diagnose, fix, validate locally, commit, push, and poll until the new run passes. Supports up to 3 retry cycles.
allowed-tools: [Bash, Read, Edit, Write, Glob, Grep, Agent]
---

# Debug CI Command

You are a CI debugging assistant for this pyocker-enter Python project. Your job is to diagnose failed GitHub Actions CI runs, fix the issues, validate locally, push, and verify the new run passes. You operate in a 6-phase feedback loop with up to 3 outer retry cycles.

## Guardrails — READ FIRST

- **Max 3 outer cycles** (diagnose → fix → push → verify). If still failing after 3, report remaining failures and suggest manual investigation.
- **Max 3 inner iterations** per local validation phase.
- **Max 60 seconds** waiting for a new CI run to appear after push.
- **Max 10 minutes** polling a single CI run.
- **NEVER check the old failed run** — always find the new run by matching commit SHA.
- **NEVER use `git add -A` or `git add .`** — always stage specific files by name.
- **Always validate locally before pushing.**
- **Always use conventional commit prefixes**: `fix:` for code/test fixes, `style:` for formatting, `ci:` for workflow changes, `docs:` for documentation, `chore:` for lock file / dependency updates.

## Phase 1: Diagnose

First, check if `gh` CLI is authenticated:

```bash
gh auth status
```

If not authenticated, tell the user to run `gh auth login` and stop.

Find recent CI runs on the current branch:

```bash
gh run list --branch $(git branch --show-current) --limit 5 --json status,conclusion,databaseId,createdAt,headSha
```

If an argument was provided to this command, use it as the run ID. Otherwise, pick the most recent failed run from the list.

**If no failed runs exist**: Report "All CI runs are green — nothing to fix!" and stop.

Get the failure details:

```bash
gh run view <run_id> --log-failed
```

Categorize the failure into one or more of:
- **uv-lock** — Lock file out of sync (`uv lock --locked` failed)
- **pre-commit** — Hook failures (case/merge conflicts, TOML/YAML/JSON validity, trailing whitespace, EOF newline)
- **ruff-check** — Python lint errors (`ruff check`)
- **ruff-format** — Python formatting drift (`ruff format --check`)
- **ty** — Type errors (`ty check`)
- **deptry** — Missing, unused, or misplaced dependency (`deptry src`)
- **pytest** — Test failures (unit tests, matrix Python 3.10–3.14)
- **mkdocs** — Documentation build failures (`mkdocs build -s`)

Extract specific file paths and line numbers from the error output.

## Phase 2: Plan Fix

For each failure type, determine the fix strategy:

| Failure | Strategy |
|---------|----------|
| uv-lock | Run `uv lock` to regenerate, then `uv lock --locked` to verify |
| pre-commit: whitespace/EOF | Re-run pre-commit — it auto-fixes; stage the modified files |
| pre-commit: TOML/YAML/JSON | Read the flagged file and fix the syntax error |
| ruff-check: auto-fixable | Run `uv run ruff check --fix src/ tests/` |
| ruff-check: manual | Read the specific file, understand context, apply targeted fix |
| ruff-format | Run `uv run ruff format src/ tests/` to auto-format |
| ty | Read the flagged file, fix the type annotation or add `# type: ignore` with a comment |
| deptry | Add missing dep with `uv add <pkg>` or remove the unused import |
| pytest | Read the failing test + the module under test; fix the implementation or test |
| mkdocs | Read the failing docs page; fix broken references, nav entries, or plugin config |

If multiple failure types exist in the same run, plan to fix ALL of them before pushing.

Read each failing file to understand context before making changes.

## Phase 3: Implement Fix

Apply targeted edits using the Edit tool. Be precise — only change what's needed to fix the CI failure.

Special cases:
- **ruff-format**: Just run `uv run ruff format src/ tests/` — it auto-formats everything.
- **ruff-check --fix**: Run `uv run ruff check --fix src/ tests/` for auto-fixable rules; read the output to find any remaining issues that need manual fixes.
- **uv-lock**: Run `uv lock` and stage `uv.lock`. Do not edit `uv.lock` by hand.
- **pre-commit auto-fixes**: After `uv run pre-commit run --all-files` modifies files, stage those specific files.
- **ty**: Follow the exact error message. Common patterns: missing return type annotation, incompatible types, undefined attribute.
- **deptry**: DEP001 = undeclared dep (add it); DEP002 = unused dep (remove it); DEP004 = misplaced in wrong group.

## Phase 4: Local Validation

Run the same checks that CI runs, individually so you can see which ones fail (max 3 iterations):

```bash
# Mirror CI 'quality' job — run each step individually
uv lock --locked
uv run pre-commit run --all-files
uv run ty check
uv run deptry src

# Mirror CI 'tests-and-type-check' job
make test

# Mirror CI 'check-docs' job
make docs-test
```

If any check fails:
1. Read the error output
2. Apply the fix
3. Re-run the failing check
4. Repeat up to 3 times

Only proceed to Phase 5 when all local checks pass.

## Phase 5: Commit & Push

Stage only the specific files you changed:

```bash
git add <file1> <file2> ...
```

Create a commit with the appropriate conventional commit prefix. Use a HEREDOC for the message:

```bash
git commit -m "$(cat <<'EOF'
<prefix>: <concise description of what was fixed>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

Push and record the SHA:

```bash
git push
PUSH_SHA=$(git rev-parse HEAD)
echo "Pushed commit: $PUSH_SHA"
```

## Phase 6: Remote Validation (Smart Polling)

**CRITICAL**: You must verify the NEW run triggered by your push, not the old failed run.

### Step 1: Initial wait

Wait 15 seconds for GitHub to register the push and create a new workflow run.

```bash
sleep 15
```

### Step 2: Find the new run by commit SHA

```bash
gh run list --branch $(git branch --show-current) --limit 5 --json databaseId,headSha,status,conclusion,createdAt
```

Filter the results for a run where `headSha` matches `$PUSH_SHA`. If not found, retry every 15 seconds up to 4 times (60 seconds total). If still not found after 60 seconds, warn the user and provide the `gh run list` command to check manually.

### Step 3: Poll until complete

Once you have the new run ID:

```bash
gh run view <new_run_id> --json status,conclusion
```

Poll every 30 seconds until `status` is `completed`. Maximum 10 minutes of polling (20 iterations).

### Step 4: Evaluate result

- **Success** (`conclusion == "success"`):
  Report victory! Show the run URL:
  ```bash
  gh run view <new_run_id> --web
  ```
  Print a summary of what was fixed and stop.

- **Failure** (`conclusion == "failure"`):
  If this is outer cycle 1 or 2, loop back to Phase 1 using the new failed run ID.
  If this is outer cycle 3, report the remaining failures and suggest manual investigation.

- **Cancelled/other**:
  Report the status and suggest the user investigate manually.

## Output Format

At each phase, provide a brief status update:

```
## Cycle N/3

### Phase 1: Diagnose
Found failed run #<id> (<timestamp>)
Failures: ruff-check (2 errors), ruff-format (formatting drift)

### Phase 2: Plan
- Fix 2 ruff-check warnings in src/pyocker_enter/cli.py
- Run ruff format to auto-format

### Phase 3: Fix
- Fixed unused import on line 5 of src/pyocker_enter/cli.py
- Ran ruff format src/ tests/

### Phase 4: Local Validation
✓ uv lock --locked passed
✓ pre-commit run --all-files passed
✓ ty check passed
✓ deptry src passed
✓ make test passed
✓ make docs-test passed

### Phase 5: Push
Committed: fix: resolve ruff lint warnings and formatting
Pushed: abc1234

### Phase 6: Verify
Waiting for new run...
Found run #<new_id> (in_progress)
Polling... (1/20)
...
✓ CI passed! https://github.com/.../actions/runs/<new_id>
```
