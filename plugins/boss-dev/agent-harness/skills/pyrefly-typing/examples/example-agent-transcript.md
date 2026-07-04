# Worked example: adopt → burn down → coverage delta

A condensed, illustrative run of the skill against a project with an existing `basedpyright` config
and a `justfile`.

## 1. Detect

```text
$ uv run "${CLAUDE_SKILL_DIR}/scripts/pyrefly_setup.py" detect --repo-root ~/dev/example-project
{
  "pyproject_exists": true,
  "python_version": "3.12",
  "project_includes": ["src", "tests"],
  "existing_type_checkers": ["basedpyright"],
  "legacy_config": null,
  "has_pyrefly_config": false,
  "pyrefly_dev_dependency": false,
  "task_runner": "just",
  "has_baseline": false,
  "settings_path_exists": false,
  "has_stop_hook": false,
  "env": {"uv": {"ok": true, "hint": null}}
}
```

No legacy config to migrate, so `apply` will hand-write `[tool.pyrefly]`.

## 2. Dry-run preview, then apply

```text
$ uv run "${CLAUDE_SKILL_DIR}/scripts/pyrefly_setup.py" apply --repo-root ~/dev/example-project --dry-run
# ... diffs reviewed with the user ...
$ uv run "${CLAUDE_SKILL_DIR}/scripts/pyrefly_setup.py" apply --repo-root ~/dev/example-project
```

Result: `[tool.pyrefly]` added (basedpyright's table untouched), `check-pyrefly` /
`pyrefly-baseline` / `pyrefly-coverage` targets appended to the `justfile`, `pyrefly-baseline.json`
generated with **41** pre-existing errors captured as the baseline (none of them block anything —
the baseline check now passes clean).

## 3. Burn down a batch

A later change introduces 12 new errors across 5 files. `check-pyrefly` fails (12 new errors since
baseline). Per `subagent-fix-loop.md`, this is fanned out by file: 5 fix subagents, each given its
file's exact errors, each self-verifying with `pyrefly check <its file>` before reporting back.

Aggregate re-check after all 5 report clean:

```text
$ just check-pyrefly
✔ 0 new errors since baseline
```

Baseline regenerated (`just pyrefly-baseline`) — committed error count unchanged at 41 (the 12 new
ones were fixed, not baselined).

## 4. Coverage delta

```text
$ just pyrefly-coverage | jq .summary.strict_coverage
# before: 0.62
# after:  0.68
```

Reported to the user as a delta ("+6 points of strict coverage this batch"), not a single global
gate.
