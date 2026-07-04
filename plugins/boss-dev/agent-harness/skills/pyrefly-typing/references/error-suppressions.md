# Error suppression syntax

Use sparingly — a suppression hides a real error from the baseline-diffed check, which weakens the
burn-down signal. Prefer fixing over suppressing; reach for these only when a fix is genuinely
out of scope for the current change (e.g. a third-party stub gap).

```python
x: int = "no"        # pyrefly: ignore              — suppress on this line (or the line above)
y: int = "no"        # pyrefly: ignore[bad-return]  — suppress a specific error kind only
# pyrefly: ignore-errors                            — file-level: suppress all errors in this file
z: int = "no"        # type: ignore                 — the standard convention; Pyrefly honours it too
```

`pyrefly suppress` can bulk-insert `# pyrefly: ignore` comments across a batch of existing errors —
useful for an initial adoption pass on a large legacy codebase, but prefer fixing new errors as they
appear rather than reaching for bulk suppression during the ongoing burn-down loop.

See the full list of error kinds (for the `ignore[<kind>]` form) at
[pyrefly.org/en/docs/error-kinds](https://pyrefly.org/en/docs/error-kinds/).
