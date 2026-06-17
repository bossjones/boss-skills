---
name: unicode-hygiene
description: Scan skill, plugin, command, agent, and marketplace files for invisible or visually-spoofed Unicode — tag characters (U+E0000–U+E007F), bidirectional overrides (Trojan Source), zero-width / format characters, and mixed-script (homoglyph) install lines. Use before committing or publishing skills/plugins, when reviewing an untrusted SKILL.md / plugin.json / agent / command, or when auditing the marketplace for hidden-instruction supply-chain payloads.
allowed-tools:
  - Bash(uv run scripts/validate-unicode-hygiene.py:*)
---

# Unicode Hygiene

Detects a supply-chain attack class that schema validation and human review both
miss: non-printing or visually-spoofed Unicode embedded in the files this repo
publishes. A reviewer sees clean text while an LLM or shell parses a hidden
instruction.

The single source of truth is the repo-root script
`scripts/validate-unicode-hygiene.py` (pure stdlib). This skill documents how to
run it; CI and pre-commit invoke the same script.

## When to Use

- Before committing or publishing a skill, plugin, command, or agent file.
- When reviewing an untrusted or externally-contributed `SKILL.md`,
  `plugin.json`, agent, or command file.
- When auditing `.claude-plugin/marketplace.json` for hidden payloads.

## Severities

- **BLOCKER** — invisible tag characters (U+E0000–U+E007F) and bidirectional
  control characters (U+202A–U+202E, U+2066–U+2069). Fail the default scan.
- **MAJOR** — other zero-width / format characters (Unicode category `Cf`).
  Reported but pass by default; fail under `--strict`.
- **MINOR** — mixed-script (homoglyph) identifiers on install-command lines, e.g.
  a Cyrillic letter hidden inside an install command. Never fail.

A leading byte-order mark (U+FEFF at offset 0) is allowed.

## How to Run

Run these from the repository root — the script path is repo-root-relative.

Scan the default repo target globs (skills, plugins, commands, agents, marketplace):

```bash
$ uv run scripts/validate-unicode-hygiene.py
```

Scan specific files or directories:

```bash
$ uv run scripts/validate-unicode-hygiene.py path/to/SKILL.md path/to/plugin.json
```

Treat MAJOR findings as failures too (stricter posture):

```bash
$ uv run scripts/validate-unicode-hygiene.py --strict
```

Report only, never fail (useful for surveying without gating):

```bash
$ uv run scripts/validate-unicode-hygiene.py --warn-only
```

Each finding prints as `path:line:col: SEVERITY category U+XXXX message`, followed
by a summary line `Scanned N file(s): X BLOCKER, Y MAJOR, Z MINOR`. Exit code is
non-zero when a BLOCKER is found (or a MAJOR under `--strict`).

## Related

The `agent-harness` PreToolUse hook (`hooks/pre_tool_use.py`) performs a
lightweight inline BLOCKER-only scan of `Write`/`Edit` content using the same two
codepoint sets, blocking edits that introduce tag characters or bidi controls
before they ever reach a file. Those two sets are defined canonically in
`scripts/validate-unicode-hygiene.py` (`TAG_RANGE` and `BIDI_CONTROLS`); keep the
hook in sync with the script.
