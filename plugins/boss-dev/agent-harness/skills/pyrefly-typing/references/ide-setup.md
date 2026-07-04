# IDE / editor setup

Optional, editor-side setup. Print these instructions as a suggested next step after CLI/config/
baseline/hook adoption is done — don't attempt to edit editor-specific settings files unless the
target editor uses a plain-JSON LSP config file the skill can safely merge into (e.g.
`coc-settings.json`). Never touch Cursor's own settings — the extension install is a manual
marketplace action.

## Cursor (and other OpenVSX-extension editors)

Search the extension marketplace for "Pyrefly" and install it directly, or link it from the
VS Code/OpenVSX listing: [marketplace.visualstudio.com/items?itemName=meta.pyrefly](https://marketplace.visualstudio.com/items?itemName=meta.pyrefly)
(extension id `meta.pyrefly`). No manual LSP wiring needed.

**Disable any competing type-checker extension** (e.g. Pyright/basedpyright's editor extension) so
the two language servers don't fight over diagnostics/hover info. This only affects the IDE
extension layer — the CLI checkers continue to coexist per the non-blocking, parallel-checker
posture (`pyrefly-cli.md`).

## Generic LSP clients (coc.nvim, or any editor without a dedicated extension)

The language server is invoked as `pyrefly lsp`:

```json
"languageserver": {
  "pyrefly": {
    "command": "pyrefly",
    "args": ["lsp"],
    "filetypes": ["python"],
    "rootPatterns": ["pyrefly.toml", "pyproject.toml", ".git"]
  }
}
```

For a project with no `[tool.pyrefly]` / `pyrefly.toml` yet, add `initializationOptions` to set a
type-checking mode explicitly:

```json
"initializationOptions": {
  "pyrefly": {
    "typeCheckingMode": "default"
  }
}
```

Accepted `typeCheckingMode` values: `auto`, `off`, `basic`, `legacy`, `default`, `strict`.

See `examples/example-lsp-settings.json` for a ready-to-paste config block, and
[pyrefly.org/en/docs/IDE/#other-editors](https://pyrefly.org/en/docs/IDE/#other-editors) for the
canonical source.
