---
paths: docs/**/*.md, ai_docs/**/*.md
---

# Documentation Standards

## Markdown Conventions

- Use ATX-style headers (`#` not underlines)
- One blank line before and after headers
- Use fenced code blocks with language specifiers
- No trailing whitespace
- Files end with a single newline

## Linting

Documentation **and agent-consumed `SKILL.md` files** are linted with `rumdl`. Configuration in
`.rumdl.toml`; entry points are `make markdown-lint` (check) and `make markdown-fix` (auto-fix).

```bash
make markdown-lint   # rumdl check .
make markdown-fix    # rumdl fmt .  (idempotent — safe to run repeatedly)
```

### Token-lean rule policy

Guiding principle: **whitespace is tokens to an LLM.** SKILL.md files are re-read on every
invocation, so the ruleset enables rules that *strip* whitespace and keep markdown parseable, and
disables rules that *pad* with whitespace or fight skill-authoring conventions.

- **Enabled — token strippers:** MD009 (trailing spaces), MD012 (multiple blank lines), MD064
  (multiple consecutive spaces), MD027 (blockquote spaces), MD038/MD039 (spaces in code/links),
  MD047 (single trailing newline).
- **Enabled — structural (small token add, big parseability):** MD022 (blanks around headings),
  MD031 (blanks around fences), MD032 (blanks around lists), MD058 (blanks around tables).
- **Disabled** (see rationale comments in `.rumdl.toml`): MD013 (line length — wrapping only adds
  newlines), MD014 (conflicts with the required `$ command` SKILL.md notation, #12781), MD033
  (skills use arbitrary `<semantic-tags>`), MD036 (intentional `**Why:**` labels), MD040 (` text`
  padding for no agent gain + corrupts nested fences), MD041 (frontmatter-first), MD046 + MD048
  (false positives / churn on nested code-fence demos).
- **Never enable** (opt-in, off by default — they ADD whitespace/tokens): **MD060** (table cell
  padding), MD063 (title-case headings), MD065 (blanks around horizontal rules).

### Nested code-fence demos

rumdl's fence parser cannot model a ```` ``` ```` block nested inside another ```` ``` ````/`~~~`
block, and `fmt` corrupts them (e.g. rewrites a closing `~~~` as `~~~text`). Skills that *document*
fenced suggestions (`github-pr-review`, `add-review-comment`) are therefore listed in `.rumdl.toml`
`exclude` (and the pre-commit hook's `exclude`) and are hand-maintained. Keep that list in sync if a
new skill teaches nested fences.

## Documentation Structure

```text
docs/
├── architecture/     # System design documents
├── checklists/       # Validation checklists
├── developer/        # Developer guides
├── ideas/            # Feature ideas and proposals
├── notes/            # Session notes and investigations
├── plans/            # Implementation plans
├── research/         # Research findings
├── reviews/          # Audit reports and reviews
└── templates/        # Document templates
```

## File Naming

- Use lowercase with hyphens: `my-document.md`
- Date prefix for time-sensitive docs: `2025-01-15-feature-design.md`
- Be descriptive but concise

## Links

- Use relative links for internal references
- Verify links work with `lychee` (config in `lychee.toml`)
