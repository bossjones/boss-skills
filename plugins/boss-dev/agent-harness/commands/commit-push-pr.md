---
description: Stage all changes, create a conventional commit, push to remote, and open a pull request via gh CLI. Use whenever you want to commit and ship current changes with a proper PR.
allowed-tools: [Bash, Read, Glob, Grep]
---

# Commit, Push, and Create PR

Stage all modified/untracked files (excluding secrets), write a conventional commit message based on the diff, push to remote, and open a GitHub PR.

## Guardrails — READ FIRST

- **NEVER stage secrets**: skip `.env`, `*.pem`, `*_key`, `credentials.*`, `*.secret` files.
- **NEVER use `git add -A` or `git add .`** — always stage specific files by name.
- **NEVER amend existing commits** — always create a new commit.
- **NEVER force push** unless the user explicitly asks.
- **NEVER silently discard a human-authored PR body.** Refresh a stale description by preserving what is still true and adding what is missing. If the body contains review notes, context, or decisions you cannot re-derive from the diff, keep them.
- **Always use conventional commit prefixes**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`.

## Phase 1: Understand the Changes

Run git status and diff in parallel to get a complete picture:

```bash
git status
git diff
git diff --cached
git log --oneline -5
```

From the output, identify:
- Which files changed and why
- Whether changes are new features, bug fixes, config, docs, etc.
- The current branch name (for the PR base)

## Phase 2: Stage Files

Stage all modified tracked files and relevant untracked files. Skip secrets and build artifacts.

```bash
# Stage each file explicitly — never use git add -A
git add <file1> <file2> ...
```

After staging, confirm with `git status` that only intended files are staged.

## Phase 3: Write the Conventional Commit

Pick the right prefix based on what changed:

| Prefix | When to use |
|--------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Code restructure, no behavior change |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests |
| `chore` | Build process, dependencies, config files |
| `ci` | CI/CD workflow changes |

Format: `<prefix>(<optional scope>): <short description>`

Keep the subject line under 72 characters. Add a body if the change needs more context.

Always end with the Co-Authored-By footer using the **current model** from the system prompt. Use a HEREDOC:

```bash
git commit -m "$(cat <<'EOF'
<prefix>: <description>

<optional body with bullet points explaining the why>

Co-Authored-By: Claude <model-name> <noreply@anthropic.com>
EOF
)"
```

## Phase 4: Push to Remote

Check if the branch has an upstream and push accordingly:

```bash
# If branch has no upstream yet:
git push -u origin $(git branch --show-current)

# If upstream already exists:
git push
```

## Phase 5: PR — Create, or Reuse and Refresh

First, check whether a PR already exists for the current branch, pulling its **full** state — not just the URL:

```bash
gh pr view --json url,title,body,state,commits,baseRefName 2>/dev/null
```

### If a PR already exists (command exits 0)

The push in Phase 4 already updated the PR's commits. But a PR that has been open for a while accumulates commits its own title and body never described — **a stale description misleads reviewers about what they are approving.** Do not just report the URL. Check the description against reality:

**1. Compare** the PR's title and body against what the branch actually contains:

```bash
git log --oneline <base>..HEAD
git diff --stat <base>...HEAD
```

**2. Judge** whether the title and body still honestly describe the **whole** branch. Signs the description is stale:

- The title describes only the earliest commit, not the branch as a whole.
- The body's Summary or Test plan refers to work that is now a small fraction of the branch.
- The body promises things the branch no longer does.

**3a. If stale** — refresh **both** the title and the body:

```bash
gh pr edit <number> \
  --title "<title covering the whole branch>" \
  --body "$(cat <<'EOF'
## Summary
- <bullet: what the branch does now, in full>

> Note: this PR grew past its original scope; description rewritten to match.

## Test plan
- [ ] <verification that matches the current diff>

## Known limitations
- <caveat a reviewer would otherwise discover the hard way>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

When writing the new body:

- **Preserve what you cannot re-derive.** Carry over review notes, context, and decisions already in the body (see the guardrail above). Rewrite the parts the diff makes false; keep the parts it does not.
- **Say the PR outgrew its scope**, in one line, when it clearly has. Quietly swapping the text hides from the reviewer *why* the PR no longer matches its own history.
- **Carry a "Known limitations" section** whenever the branch has any: things not yet verified, caveats a reviewer would otherwise hit the hard way. An honest PR body beats a flattering one.

Report in the summary that the description was refreshed.

**3b. If still accurate** — leave the title and body alone, and **say so explicitly** in the summary. "Already accurate" is a real outcome and the user should hear it; silence is not.

### If no PR exists (command exits non-zero)

Create one with `gh pr create`. Base the PR on `main` unless the branch name suggests otherwise.

```bash
gh pr create \
  --title "<same as commit subject line>" \
  --body "$(cat <<'EOF'
## Summary
- <bullet 1: what changed>
- <bullet 2: why it matters>

## Test plan
- [ ] <specific thing to verify>
- [ ] <another verification step>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

## Output Format

Provide a brief summary at the end:

```text
**Committed:** `<prefix>: <description>`
**Pushed:** <short SHA>
**PR:** <URL>  ← (existing, description refreshed) | (existing, already accurate) | (new)
```

If `gh` is not authenticated, tell the user to run `gh auth login` and stop before trying to create the PR.
