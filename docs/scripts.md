# Scripts

Python scripts in the `scripts/` directory. All use PEP 723 inline metadata and run via `uv run`.

| Script | Description | Dependencies | Python |
|--------|-------------|--------------|--------|
| `eval-skills.py` | Quality-gates skills with `plugin-eval` (score / certify / compare / init) | none | >=3.13 |
| `markdown_formatter.py` | Fixes missing language tags and spacing in markdown files | none | >=3.11 |
| `setup_twitter_auth.py` | Manual Twitter/X login and cookie extraction via Playwright | playwright | >=3.13 |
| `skill_validation.py` | Validates SKILL.md files against agent skills best practices | pyyaml, rich | >=3.13 |
| `verify-structure.py` | Validates Claude Code marketplace structure and plugin manifests | jsonschema, pyyaml, rich | >=3.11 |

`eval-skills.py` declares no PEP 723 dependencies — it pulls `plugin-eval` on
demand via `uvx`.

## Usage

### eval-skills.py

Discovers every skill under `plugins/`, runs `plugin-eval` against each, prints
a score table, and can fail a build when a skill drops below a threshold.
`plugin-eval` is fetched on demand via `uvx` — nothing is vendored.

```text
./scripts/eval-skills.py                              # Report all skills, never fails
./scripts/eval-skills.py --threshold 57               # Fail if any skill < 57
./scripts/eval-skills.py --skill plugins/.../foo      # Score a single skill
./scripts/eval-skills.py --command certify plugins/.../foo   # Certify one skill
```

| Exit code | Meaning |
|-----------|---------|
| 0 | All skills met the threshold, or no threshold set |
| 1 | A skill scored below `--threshold` or errored; or a streamed subcommand failed |
| 2 | Usage error (bad `--skill`, wrong target count, no skills found) |

See [`eval-skills.md`](eval-skills.md) for the full command reference, the
evaluation-layer matrix, and Makefile/CI integration.

### markdown_formatter.py

Fixes missing language tags on fenced code blocks and spacing issues.

```text
./scripts/markdown_formatter.py file.md              # Fix a single file
./scripts/markdown_formatter.py file1.md file2.md    # Fix multiple files
echo '{"tool_input":{"file_path":"f.md"}}' | ./scripts/markdown_formatter.py  # Hook mode
./scripts/markdown_formatter.py --blocking file.md   # Exit 2 when changes made
```

| Exit code | Meaning |
|-----------|---------|
| 0 | No changes or blocking mode disabled |
| 2 | Changes made in blocking mode |

### setup_twitter_auth.py

Opens a Chromium browser for manual Twitter/X login, then saves session cookies for use by other tools.

```text
uv run playwright install chromium   # First-time setup
./scripts/setup_twitter_auth.py      # Launch browser and log in
```

### skill_validation.py

Recursively finds all `SKILL.md` files under a directory and validates them against 16 rules covering required fields, description quality, structure, and the parser bug (#12781).

```text
./scripts/skill_validation.py .            # Validate all skills
./scripts/skill_validation.py . --strict   # Warnings become errors (for CI)
```

| Exit code | Meaning |
|-----------|---------|
| 0 | All checks passed (warnings OK in normal mode) |
| 1 | Errors found, or warnings in strict mode |

### verify-structure.py

Validates marketplace.json, plugin.json manifests, skill/command/agent/hook definitions, and MCP server configs.

```text
./scripts/verify-structure.py            # Normal mode
./scripts/verify-structure.py --strict   # Warnings become errors (for CI)
```

| Exit code | Meaning |
|-----------|---------|
| 0 | All checks passed (warnings OK in normal mode) |
| 1 | Errors found, or warnings in strict mode |
