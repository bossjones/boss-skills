# Scripts

Python scripts in the `scripts/` directory. All use PEP 723 inline metadata and run via `uv run`.

| Script | Description | Dependencies | Python |
|--------|-------------|--------------|--------|
| `markdown_formatter.py` | Fixes missing language tags and spacing in markdown files | none | >=3.11 |
| `setup_twitter_auth.py` | Manual Twitter/X login and cookie extraction via Playwright | playwright | >=3.13 |
| `skill_validation.py` | Validates SKILL.md files against agent skills best practices | pyyaml, rich | >=3.13 |
| `verify-structure.py` | Validates Claude Code marketplace structure and plugin manifests | jsonschema, pyyaml, rich | >=3.11 |

## Usage

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
