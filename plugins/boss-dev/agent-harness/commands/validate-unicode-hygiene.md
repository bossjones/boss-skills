---
description: Scan files for invisible or visually-spoofed Unicode (tag characters, bidi overrides, zero-width / format chars, homoglyph install lines) using scripts/validate-unicode-hygiene.py. Defaults to the repo target globs; pass paths to scan specific files.
argument-hint: "[paths...] [--strict] [--warn-only]"
allowed-tools:
  - Bash(uv run scripts/validate-unicode-hygiene.py:*)
---

# Validate Unicode Hygiene

Run the repo-root unicode-hygiene validator over `$ARGUMENTS`. With no arguments
it scans the default target globs (skills, plugins, commands, agents,
marketplace); the malicious test fixtures are deliberately excluded.

Run from the repository root:

```bash
uv run scripts/validate-unicode-hygiene.py $ARGUMENTS
```

Report the per-file findings and the `Scanned N file(s): X BLOCKER, Y MAJOR,
Z MINOR` summary. The command exits non-zero when a BLOCKER is found (invisible
tag characters or bidirectional controls), or when a MAJOR is found under
`--strict`. MINOR (homoglyph) findings never fail.

See the [`unicode-hygiene`](../skills/unicode-hygiene/SKILL.md) skill for the
severity model and the threat it guards against.
