# basedpyright-lsp

LSP plugin that wires [basedpyright](https://docs.basedpyright.com/) into Claude Code, giving Claude real-time Python diagnostics, hover docs, go-to-definition, and find-references while editing Python code.

## Why basedpyright (not pyright)?

basedpyright is a community fork of Microsoft's pyright that:

- Implements a **strict superset** of pyright's checks (everything pyright catches, basedpyright catches too, plus extra rules like `reportImplicitOverride`).
- Re-adds features Microsoft removed from pyright's LSP surface (full semantic tokens, inlay hints, baseline files).
- Reads the same configuration (`pyrightconfig.json` and `[tool.pyright]` / `[tool.basedpyright]` in `pyproject.toml`) — switching is zero-cost if you already use pyright.
- Ships a single binary (`basedpyright-langserver`) installable via `uv` — no Node toolchain required.

Anthropic's official marketplace already provides `pyright-lsp`, so this plugin exists to cover basedpyright users specifically. If you want vanilla pyright instead, install `pyright-lsp` from the official marketplace.

## Prerequisites

- **Claude Code 2.1.50 or later** (LSP plugin support).
- **basedpyright installed and on `PATH`**:

  ```bash
  uv tool install basedpyright       # recommended
  # or
  pip install basedpyright           # if you don't use uv
  ```

  Verify the binary is available:

  ```bash
  basedpyright-langserver --help
  ```

## Installation

Add the marketplace and install the plugin:

```text
/plugin marketplace add bossjones/boss-skills
/plugin install basedpyright-lsp@boss-skills
```

Restart Claude Code (or run `/reload-plugins`) so the LSP server attaches.

## Configuration

This plugin ships **no opinions** about strictness. Configure basedpyright per-project the same way you'd configure pyright:

- `pyrightconfig.json` at the project root, **or**
- `[tool.basedpyright]` (or `[tool.pyright]`) in `pyproject.toml`

Example `pyproject.toml`:

```toml
[tool.basedpyright]
include = ["src"]
pythonVersion = "3.13"
typeCheckingMode = "strict"
reportImplicitOverride = "error"
```

See the [basedpyright configuration docs](https://docs.basedpyright.com/latest/configuration/config-files/) for the full option list.

## Verification

After installing the plugin:

1. Open any `.py` file in a project that uses basedpyright.
2. Run `/plugin` and check the **Errors** tab is clean for `basedpyright-lsp`. `Executable not found in $PATH` means the prerequisite step above failed — install basedpyright and restart.
3. Introduce an obvious type error (`x: int = "string"`) and confirm Claude sees a diagnostic.

## Troubleshooting

- **`Executable not found in $PATH`** — basedpyright isn't installed for the shell Claude Code launches. `uv tool install basedpyright` exposes the binary on the default uv tool `PATH`; confirm with `which basedpyright-langserver`.
- **LSP doesn't attach** — older Claude Code versions need `npx tweakcc --apply` once to enable LSP plugin support. Upgrade to 2.1.50+ if possible.
- **No diagnostics surface** — confirm your project has a basedpyright config (or remove all configs to use defaults). Pure-Python files with no project root may not trigger analysis.

## License

MIT
