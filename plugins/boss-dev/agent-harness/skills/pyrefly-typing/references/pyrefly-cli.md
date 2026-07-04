# Pyrefly CLI reference

Verified against the `facebook/pyrefly` source (`pyrefly/lib/commands/all.rs`), not just the docs
site, since the docs can lag a release.

## Subcommands

| Command | Purpose | Notes |
|---|---|---|
| `pyrefly check [paths...]` | Type-check the project | `--baseline <file>` / `--update-baseline` (see below) |
| `pyrefly init` | Generate `[tool.pyrefly]`, optionally migrating an existing checker | `--migrate-from {auto,mypy,pyright}` (default `auto` — tries mypy, then pyright), `--dry-run`, `--print-config` |
| `pyrefly infer <path>` | Autotype: insert inferred annotations | Review the diff in small batches — infer can surface *new* errors |
| `pyrefly coverage report [paths...]` | Type-coverage report (JSON) | **Not** a bare top-level `coverage` command — it's `coverage report`. `pyrefly report` still exists but is a **hidden, deprecated alias** |
| `pyrefly lsp` | Language server | Used directly by generic LSP clients (coc.nvim, etc.) — see `ide-setup.md` |
| `pyrefly suppress` | Bulk-insert suppression comments | See `error-suppressions.md` |
| `pyrefly stubgen` | Generate `.pyi` stubs | |
| `pyrefly snippet`, `dump-config`, `buck-check`, `bazel-check`, `tsp` | Specialized/build-system integrations | Out of scope for this skill |

## `check` baseline flags

```text
pyrefly check --baseline pyrefly-baseline.json --summarize-errors  # fail only on errors new since baseline
pyrefly check --baseline pyrefly-baseline.json --update-baseline  # regenerate baseline from current errors
```

- `--baseline <file>` takes a path.
- `--summarize-errors` prints a top-files/top-error-kinds rollup after the per-error output —
  every task-runner target and the feedback loop's step 1 use this flag for the day-to-day check.
- `--update-baseline` **requires** `--baseline` to also be passed (the CLI rejects it alone) — never
  emit one without the other.
- The config file can also set a default `baseline` key; an explicit `--baseline` flag overrides it.

## `init` migration

`pyrefly init --migrate-from {auto,mypy,pyright}` does a real field-by-field migration — separate
migrator modules exist per setting (`project_includes`, `project_excludes`, `search_path`,
`python_version`, `python_platform`, `python_interpreter`, `site_package_path`, `error_codes`,
`ignore_missing_imports`, `untyped_def_behavior`, `sub_configs`). It is not a blind copy. Use
`--dry-run` to preview and `--print-config` to emit the resulting TOML to stdout before committing to
it.

## `coverage report` JSON shape

Schema version `0.2`. Top level:

```json
{
  "schema_version": "0.2",
  "module_reports": [ /* per-module detail */ ],
  "summary": {
    "n_modules": 0,
    "coverage": 0.0,
    "strict_coverage": 0.0
    /* plus other SlotCounts/SymbolCounts fields */
  }
}
```

`summary.strict_coverage` and `summary.coverage` are direct sibling fields — the burn-down loop's
`jq .summary.strict_coverage` path (see `feedback-loop.md`) is correct as written.

## Capabilities coexistence

Pyrefly bundles typeshed and popular third-party stubs and has zero-config support for Pydantic v2,
attrs, and pytest. It is designed to run **alongside** other checkers, not replace them — see
[Are you really expected to run five type-checkers now?](https://pyrefly.org/blog/too-many-type-checkers/).
This skill never edits or gates `[tool.mypy]`, `[tool.pyright]`, `[tool.basedpyright]`, or
`[tool.ty]` in the target repo.
