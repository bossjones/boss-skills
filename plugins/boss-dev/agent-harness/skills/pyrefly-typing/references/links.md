# Pyrefly reference links

## Docs

- Homepage — https://pyrefly.org/
- Docs intro — https://pyrefly.org/en/docs/
- Installation — https://pyrefly.org/en/docs/installation/
- Typing for Python Developers — https://pyrefly.org/en/docs/typing-for-python-developers/
- Import Resolution — https://pyrefly.org/en/docs/import-resolution/
- IDE Installation — https://pyrefly.org/en/docs/IDE/
- IDE Installation: Other editors (Cursor/OpenVSX, generic LSP) — https://pyrefly.org/en/docs/IDE/#other-editors
- Cursor/VS Code marketplace extension (`meta.pyrefly`) — https://marketplace.visualstudio.com/items?itemName=meta.pyrefly
- Pydantic Support — https://pyrefly.org/en/docs/pydantic/
- attrs Support — https://pyrefly.org/en/docs/attrs/
- Pytest Support — https://pyrefly.org/en/docs/pytest/
- Error Suppressions — https://pyrefly.org/en/docs/error-suppressions/
- Error Kinds — https://pyrefly.org/en/docs/error-kinds/
- Infer / autotype — https://pyrefly.org/en/docs/autotype/
- Coverage / report — https://pyrefly.org/en/docs/report/
- Stub Generation — https://pyrefly.org/en/docs/stubgen/
- Sandbox — https://pyrefly.org/sandbox/

## Blog & talks

- Blog index — https://pyrefly.org/blog/
- Adding Pyrefly to Your Agentic Loop — https://pyrefly.org/blog/pyrefly-agentic-loop/ (basis for the Stop hook)
- Talk: Type Checking in Agentic Workflows — https://pyrefly.org/blog/type-checking-agentic-workflows/
- Pyrefly v1.1 is here! — https://pyrefly.org/blog/v1.1/
- Define less, check more: Pyrefly now speaks attrs — https://pyrefly.org/blog/pyrefly-attrs/
- Are you really expected to run five type-checkers now? — https://pyrefly.org/blog/too-many-type-checkers/
- Making Type Coverage Visible in Dify's CI — https://pyrefly.org/blog/dify-pyrefly-coverage-ci/ (model for the deferred `ci-comments.md`)
- Third-Party Stubs bundled with Pyrefly — https://pyrefly.org/blog/stubs/
- Give your Python IDE a Glow-Up with Pyrefly — https://pyrefly.org/blog/2025/09/15/ide-extension/

## Source & announcement

- GitHub (pyrefly) — https://github.com/facebook/pyrefly
- Pre-commit hook — https://github.com/facebook/pyrefly-pre-commit
- Meta engineering announcement — https://engineering.fb.com/2025/05/15/developer-tools/open-sourcing-pyrefly-a-faster-python-type-checker-written-in-rust/

## Deferred scope

The GitHub Actions PR-comment workflow pair (type-error diff + type-coverage diff) is not built in
this pass. If it's picked up later, the reusable §2 generic template and both helper scripts
(`pyrefly_diagnostics.py`, `pyrefly_type_coverage.py`) live in a sibling project's spec — see the
implementation-approach comment on
[issue #40](https://github.com/bossjones/boss-skills/issues/40) for where that prior art lives.
