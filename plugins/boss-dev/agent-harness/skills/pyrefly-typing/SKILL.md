---
name: pyrefly-typing
description: Adopt Pyrefly (Meta's Rust-based Python type checker) into a target `uv` Python project as a non-blocking, agent-driven typing feedback loop, alongside whatever type checker it already uses (mypy/pyright/basedpyright/ty) — never replacing it. Use when asked to "adopt pyrefly", "set up pyrefly typing", "add a pyrefly feedback loop", "burn down pyrefly errors", or "wire a pyrefly Stop hook" into a project. This skill configures a *target* repo (pyproject.toml, baseline, task-runner targets, optional Stop hook) — it never touches boss-skills itself.
disable-model-invocation: true
argument-hint: "<target-repo-path> [--with-stop-hook] [--dry-run]"
allowed-tools:
  - Bash(uv run:*)
  - Bash(uv add:*)
  - Bash(git rev-parse:*)
effort: medium
---

# Pyrefly Typing

Adopts [Pyrefly](https://pyrefly.org/) into a **target** `uv` Python project as a second,
non-blocking type-checking signal — coexisting with whatever checker that project already runs,
never gating its existing lint/check/CI. Think of it as an installer + ongoing burn-down loop: point
it at project X and it wires up `[tool.pyrefly]`, a committed baseline, standalone task-runner
targets, an optional Stop hook, and a fix-verify subagent loop for X.

**This skill configures other repos, not `boss-skills`.** `boss-skills` has no `[tool.pyrefly]` and
doesn't need one — never run `apply` with `--repo-root` pointing at this repo.

## Variables

- `TARGET_REPO` — path to the `uv` Python project to adopt Pyrefly into (required).
- `WITH_STOP_HOOK` — whether to merge the Stop hook into `TARGET_REPO/.claude/settings.json`
  (opt-in; ask the user, default no).
- `MIGRATE_FROM` — `auto` / `mypy` / `pyright` / `none` (default `auto`: use `pyrefly init
  --migrate-from` when `detect` reports a `legacy_config`, otherwise hand-write `[tool.pyrefly]`).

## When to use

- Adopting Pyrefly in a repo for the first time ("adopt pyrefly", "set up pyrefly typing").
- Adding the agentic feedback loop described in Pyrefly's own
  [agentic-loop post](https://pyrefly.org/blog/pyrefly-agentic-loop/) ("add a pyrefly Stop hook").
- Working through a batch of baseline type errors ("burn down pyrefly errors").
- IDE/editor integration questions for Pyrefly (Cursor, coc.nvim, generic LSP).

## Workflow

See [examples/example-agent-transcript.md](examples/example-agent-transcript.md) for a worked
end-to-end run of the steps below.

### 0. Confirm the target is a git repo

```text
$ git -C <TARGET_REPO> rev-parse --is-inside-work-tree
```

`apply` backs up every file it touches, but a git-tracked target makes every change trivially
reviewable (`git diff`) and revertible. If this fails, tell the user `TARGET_REPO` isn't a git
repository before writing anything.

### 1. Detect current state (read-only)

```text
$ uv run "${CLAUDE_SKILL_DIR}/scripts/pyrefly_setup.py" detect --repo-root <TARGET_REPO>
```

Prints a JSON report: Python version floor, real `src`/`tests` layout, every existing type-checker
table already configured (`ty`, `basedpyright`, `mypy`, `pyright` — these are **never** touched),
whether a migratable legacy config exists, whether `[tool.pyrefly]` / a dev dependency / a committed
baseline / a Stop hook already exist, the detected task runner (`just` / `make` / `npm`), and `uv`
availability.

### 2. Decide the config path

- If `legacy_config` is `mypy` or `pyright`, prefer letting `apply` run `pyrefly init
  --migrate-from <checker>` (real field-by-field migration) over hand-writing `[tool.pyrefly]` — see
  [references/pyproject-config.md](references/pyproject-config.md).
- If `existing_type_checkers` is non-empty, tell the user those tables stay byte-for-byte
  unchanged — Pyrefly is a parallel, non-blocking signal, not a replacement (see
  [references/pyrefly-cli.md](references/pyrefly-cli.md) for the full capability table and why
  coexistence is the intended posture).
- Ask whether to opt into `--with-stop-hook`. Default is no; explain what it does and how to
  disable it later — see [references/hook-setup.md](references/hook-setup.md).

### 3. Preview with `--dry-run`

Always preview before writing — nothing is written, and each changed area's result carries a unified
`diff` (or the exact command that would run, for `uv add` / `pyrefly init` / baseline generation):

```text
$ uv run "${CLAUDE_SKILL_DIR}/scripts/pyrefly_setup.py" apply --repo-root <TARGET_REPO> --dry-run [--with-stop-hook]
```

Show the diffs to the user and confirm before applying.

### 4. Apply

Same command, drop `--dry-run`:

```text
$ uv run "${CLAUDE_SKILL_DIR}/scripts/pyrefly_setup.py" apply --repo-root <TARGET_REPO> [--with-stop-hook]
```

This runs `uv add --dev pyrefly` (skipped if already a dependency), writes or migrates
`[tool.pyrefly]`, adds standalone `check-pyrefly` / `pyrefly-baseline` / `pyrefly-coverage` targets to
the detected task runner (never wired into existing `lint`/`check`/CI targets), optionally merges the
Stop hook, and generates the initial committed baseline. Every modified file is backed up to
`<file>.backup.<timestamp>` first.

### 5. Burn down baseline errors

Follow the 5-step loop in [references/feedback-loop.md](references/feedback-loop.md) (see
regressions → fix → burn down → track coverage → automate via the Stop hook). For a batch of new
baseline errors, apply the fan-out thresholds in
[references/subagent-fix-loop.md](references/subagent-fix-loop.md): small batches fixed in the
current context, larger batches fanned out one subagent per file or error-kind cluster, each
subagent self-verifying with `pyrefly check` on its own files before a final aggregate re-check.
Suppression syntax for anything that shouldn't block the burn-down is in
[references/error-suppressions.md](references/error-suppressions.md).

### 6. IDE setup (optional next step)

After adoption, print — don't silently apply — the editor setup notes in
[references/ide-setup.md](references/ide-setup.md) (Cursor/OpenVSX extension, generic LSP config).
Only merge a plain-JSON LSP config file (e.g. `coc-settings.json`) directly if the target editor
uses one; never touch Cursor's own settings.

## Reference files

| File | When to consult |
|---|---|
| [references/pyrefly-cli.md](references/pyrefly-cli.md) | Full CLI capability table (`check`, `init`, `infer`, `coverage`, `stubgen`, `lsp`, `suppress`) and exact flags. |
| [references/pyproject-config.md](references/pyproject-config.md) | `[tool.pyrefly]` kebab-case key reference and the migrate-vs-hand-write decision. |
| [references/feedback-loop.md](references/feedback-loop.md) | The 5-step regressions→fix→burn-down→coverage→automate loop. |
| [references/hook-setup.md](references/hook-setup.md) | Target-repo Stop-hook snippet, merge-not-clobber rule, how to disable, pre-commit alternative. |
| [references/subagent-fix-loop.md](references/subagent-fix-loop.md) | Fan-out thresholds for fixing a batch of baseline errors. |
| [references/error-suppressions.md](references/error-suppressions.md) | Inline/file-level suppression syntax. |
| [references/ide-setup.md](references/ide-setup.md) | Cursor/OpenVSX + generic LSP editor setup. |
| [references/links.md](references/links.md) | Full URL index (docs, blog posts, source repos). |

## Non-goals

- Never makes Pyrefly blocking in the target repo's existing CI/lint — it only ever adds new,
  standalone targets.
- Never decides whether Pyrefly eventually replaces the target's existing checker — coexistence
  only.
- The GitHub Actions PR-comment workflow pair (type-error diff + type-coverage diff, adapted from
  `langgenius/dify`'s CI) is **not** built by this pass — it's deferred to a follow-up
  (`references/ci-comments.md` does not exist yet).

## Usage

```
/pyrefly-typing ~/dev/example-project
/pyrefly-typing ~/dev/example-project --with-stop-hook
/pyrefly-typing ~/dev/example-project --dry-run
```

Flags: $ARGUMENTS
