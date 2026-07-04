---
name: pyrefly-typing
description: Adopt Pyrefly (Meta's Rust-based Python type checker) into a target `uv` Python project as a non-blocking, agent-driven typing feedback loop, alongside whatever type checker it already uses (mypy/pyright/basedpyright/ty) — never replacing it. Use when asked to "adopt pyrefly", "set up pyrefly typing", "add a pyrefly feedback loop", "burn down pyrefly errors", or "wire a pyrefly Stop hook" into a project. This skill configures a *target* repo (pyproject.toml, baseline, task-runner targets, optional Stop hook) — it never touches boss-skills itself.
disable-model-invocation: true
argument-hint: "<target-repo-path> [--with-stop-hook] [--dry-run]"
allowed-tools:
  - Bash(uv run:*)
  - Bash(uv add:*)
  - Bash(git rev-parse:*)
  - Bash(git -C:*)
  - Bash(command -v:*)
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

### 0. Confirm the target is a git repo, and that `uv` is available

```text
$ git -C <TARGET_REPO> rev-parse --is-inside-work-tree
$ command -v uv
```

`apply` backs up every file it touches, but a git-tracked target makes every change trivially
reviewable (`git diff`) and revertible. If the first command fails, tell the user `TARGET_REPO`
isn't a git repository before writing anything.

Every step below shells out to `uv` — to run this skill's own PEP 723 script, and, inside
`apply`, to run `uv add --dev pyrefly` in `TARGET_REPO`. If `command -v uv` prints nothing, stop
here and tell the user to install `uv` (<https://docs.astral.sh/uv/>) before continuing. Step 1's
`detect` JSON echoes the same check under `env.uv.ok`/`env.uv.hint` as a second confirmation once
`uv` is reachable.

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
Stop hook, and generates the initial committed baseline. Hand-written config, task-runner target, and
Stop-hook changes are each backed up to `<file>.backup.<timestamp>` before writing; the `uv add` and
`pyrefly init --migrate-from` paths mutate `pyproject.toml` directly without their own backup step, so
step 0's git-repo check is the safety net for those two — review `git diff` before committing.

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
| [references/subagent-fix-loop.md](references/subagent-fix-loop.md) | Fan-out thresholds for fixing a batch of baseline errors. See also `skills/boss-security-review`, whose fan-out size heuristic this mirrors. |
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

## Troubleshooting

| Symptom | Fix |
|---|---|
| `detect`'s `env.uv.ok` is `false`, or `command -v uv` in step 0 prints nothing | `uv` isn't on `PATH`. Install it (<https://docs.astral.sh/uv/>) and stop — do not run `apply` until it is. |
| Step 0's `git rev-parse --is-inside-work-tree` fails | `TARGET_REPO` isn't a git repo. Stop and tell the user before writing anything. |
| `apply`'s summary shows `"config": {"changed": false, "already_present": true}` but `[tool.pyrefly]` looks wrong or incomplete | `apply` never edits an existing `[tool.pyrefly]` table, even a broken one — it only skips writing. Fix or delete the fragment by hand, then re-run. |
| `apply --with-stop-hook` fails with a message like `<path> contains invalid JSON ...; refusing to overwrite` | The target's `.claude/settings.json` is malformed; the script refuses to touch it. Fix or remove that file, then re-run. |
| Summary JSON's `baseline.returncode` is non-zero even though `apply` itself exited 0 | Baseline generation failed independently (check `baseline.stdout`/`baseline.stderr`). Fix the underlying issue, then re-run with `--skip-baseline`, or generate it by hand: `uv run pyrefly check --baseline pyrefly-baseline.json --update-baseline`. |

## Usage

```
/pyrefly-typing ~/dev/example-project
/pyrefly-typing ~/dev/example-project --with-stop-hook
/pyrefly-typing ~/dev/example-project --dry-run
```

`apply` also accepts `--project-includes`, `--python-version`, `--task-runner`, `--migrate-from`,
and `--skip-baseline` (all optional, auto-detected by default) — see Workflow step 2 and
[references/pyproject-config.md](references/pyproject-config.md).

Flags: $ARGUMENTS
