# External skills: mattpocock-skills

The Matt Pocock engineering skills (`grill-with-docs`, `triage`, `to-tickets`, `tdd`, and the rest)
are **not part of this repository**. They are consumed as a plugin installed at **user scope on
both harnesses**, and must **never** be copied into `.claude/skills/` — that was the old
skills.sh-vendored arrangement, removed in 2026-08 because the copies drifted stale (see
`specs/remove-vendored-mattpocok-skills.md` and recovery commit `c9b0237`).

## Topology

| Harness | Install | Update |
|---------|---------|--------|
| Claude Code | `claude plugin install mattpocock-skills@claude-plugins-official --scope user` | auto-updates on upstream release (official marketplace, SHA-pinned) |
| Copilot CLI | `copilot plugin install mattpocock/skills` (direct repo — Step 8a) | `copilot plugin update mattpocock-skills` |

Both read upstream's `.claude-plugin/plugin.json` and install the same 25 promoted skills.
Verified 2026-08-31: Copilot loads all 25 from the manifest's explicit `skills` array
("Installed 25 skills"), so no fallback staging was needed.

Skills are invoked **namespaced**: `/mattpocock-skills:grill-with-docs`,
`/mattpocock-skills:code-review`, etc. `CLAUDE.md`'s `## Agent skills` section and
`docs/agents/*.md` document the repo-side contract (issue tracker, triage labels, domain docs)
that these skills read at runtime.

## Known caveats

- **Copilot direct installs are deprecated.** The install emitted: *"Direct plugin installs
  (repos, URLs, local paths) are deprecated. Only plugin@marketplace installs will be supported in
  a future release."* When that lands, re-install via upstream's own marketplace:
  `copilot plugin marketplace add mattpocock/skills && copilot plugin install
  mattpocock-skills@mattpocock` (note: upstream's marketplace entry lacks a `version` field, which
  Copilot may or may not accept).
- **Copilot's `copilot skill list` dedupes bare names.** After install, only one `code-review`
  line shows (mattpocock's), hiding the `code-review@claude-plugins-official` plugin's skill from
  the *listing*. Use the namespaced slash-picker forms to address each one unambiguously.
- **Version skew.** Claude tracks the official marketplace's pinned SHA; Copilot tracks the
  default branch at install time. Check Claude's pin with:
  `python3 -c "import json;from pathlib import Path;d=json.loads((Path.home()/'.claude/plugins/installed_plugins.json').read_text());print([e.get('gitCommitSha') for k,v in d['plugins'].items() if 'mattpocock' in k for e in v])"`

## Renamed / removed skills (old vendored name → today)

| Old name (vendored until 2026-08) | Now |
|---|---|
| `diagnose` | `mattpocock-skills:diagnosing-bugs` |
| `to-issues` | `mattpocock-skills:to-tickets` |
| `to-prd` | `mattpocock-skills:to-spec` |
| `review` | `mattpocock-skills:code-review` |
| `caveman`, `design-an-interface`, `edit-article`, `qa`, `write-a-skill`, `zoom-out` | deleted upstream — recoverable only from commit `c9b0237` |
| `grill-me`, `grill-with-docs`, `handoff`, `improve-codebase-architecture`, `prototype`, `setup-matt-pocock-skills`, `teach`, `triage` | same name, `mattpocock-skills:` prefix |
