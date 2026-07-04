# `[tool.pyrefly]` config reference

## Key naming

Pyrefly's `ConfigFile` struct is `#[serde(rename_all = "kebab-case")]` — every key in
`[tool.pyrefly]` is **kebab-case**, not snake_case:

```toml
[tool.pyrefly]
project-includes = ["src", "tests"]   # the real source/test dirs — detect, don't assume
python-version = "3.12"                # from .python-version, else the requires-python floor
```

See [../examples/example-pyproject-snippet.toml](../examples/example-pyproject-snippet.toml) for a
full worked example alongside an untouched `[tool.basedpyright]` table and the justfile targets.

Confirmed keys (non-exhaustive; see the `facebook/pyrefly` source clone,
`crates/pyrefly_config/src/config.rs`, for the full flattened set): `project-includes`,
`project-excludes`, `disable-project-excludes-heuristics`, `search-path`,
`disable-search-path-heuristics`, `enable-fallback-search-path`, `typeshed-path`, `baseline`,
`output-format`, `preset`, `sub-config`, `use-ignore-files`, `build-system`, `min-severity`,
`skip-lsp-config-indexing`, `extra-file-extensions`, `python-interpreter`, `conda-environment`,
`skip-interpreter-query`, `python-platform`, `python-version`, `site-package-path`, `errors`,
`permissive-ignores`, `enabled-ignores`, `ignore-missing-imports`, `check-unannotated-defs`,
`infer-return-types`, `disable-type-errors-in-ide`, `ignore-errors-in-generated-code`.

## Detecting the real layout — never assume `src`/`tests`

`pyrefly_setup.py`'s `detect_project_includes()` checks which of `src` / `tests` actually exist at
the repo root and falls back to `["."]` if neither does. Always use the `detect` command's
`project_includes` field rather than hardcoding the issue's example paths.

## Migrate vs. hand-write

If `detect` reports a `legacy_config` (`mypy` or `pyright` — meaning `mypy.ini`/`[tool.mypy]` or
`pyrightconfig.json`/`[tool.pyright]` exists), prefer `pyrefly init --migrate-from <checker>` over
hand-writing `[tool.pyrefly]`. It performs a real field-by-field migration (includes, excludes,
search path, python version/platform/interpreter, site-package path, error codes,
ignore-missing-imports, untyped-def behavior, sub-configs) rather than a blind copy. Use
`--dry-run`/`--print-config` first to preview.

If there's no legacy config to migrate, `pyrefly_setup.py apply` hand-writes a minimal
`[tool.pyrefly]` block, appended as a new table at EOF — it only ever *adds* a table, never edits an
existing `[tool.basedpyright]` / `[tool.mypy]` / `[tool.pyright]` / `[tool.ty]` table.

## Never touch other checkers' config

`ty` (Astral's checker) configures under `[tool.ty]` (e.g. `[tool.ty.environment]`), and
`basedpyright` under `[tool.basedpyright]`. A project may run several of these simultaneously (see
`adguardctl`'s `ty` + `basedpyright` setup) — Pyrefly is layered on top as a third, non-blocking
signal. Detection (`detect_existing_type_checkers()`) reports which are present purely for the
skill's own summary to the user; it never edits them.
