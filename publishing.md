# Publishing to the boss-skills marketplace

`boss-skills` is a Claude Code **plugin marketplace**, not a PyPI package — there is no wheel to
upload. "Publishing" here means making a new or updated plugin available to anyone who has added the
marketplace. That happens entirely through the repo: install consumers pick up changes from the
default branch (or when they run `/plugin marketplace update boss-skills`).

The single rule that gates whether users actually receive an update: **the plugin's `version` must be
bumped in both `plugin.json` and its `.claude-plugin/marketplace.json` entry.** If the version
doesn't change, installed clients keep the old copy.

## Publishing a new plugin

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full scaffold → validate → document flow. In short:

1. Scaffold with `/create-plugin <category>/<plugin-name>` (or copy `templates/plugin-template/`).
2. Register it in `.claude-plugin/marketplace.json` (the command does this for you).
3. Validate: `make verify-structure`, `make lint`, `make eval`.
4. Document it (`docs/plugins/<name>.md` + both plugin tables).
5. Commit and merge to the default branch.

The initial publish is `v0.1.0` by convention, with `plugin.json.version` and the marketplace entry
in parity.

## Releasing an update to an existing plugin

1. Make your change to the plugin's components.
2. Run the [`version-bump-reviewer`](.claude/skills/version-bump-reviewer/SKILL.md) skill (it also
   auto-triggers via a hook on component edits). It classifies the change as major/minor/patch and
   bumps **both** `plugin.json.version` and the matching `marketplace.json` entry in lockstep, then
   writes a conventional-commit message.
3. Validate: `make verify-structure` and `make lint`.
4. Refresh the changelog:

   ```bash
   make changelog-preview     # preview the unreleased section
   make changelog             # regenerate CHANGELOG.md from conventional commits (git-cliff)
   ```

5. Commit and merge. Consumers receive the update on their next
   `/plugin marketplace update boss-skills` (or automatically if they enabled autoUpdate).

## Updating an external (pinned) plugin

External plugins (e.g. [`github-pr-review`](docs/plugins/github-pr-review.md)) are referenced as a
`git-subdir` source pinned to a `ref` + `sha`. They never update silently — taking a newer upstream
release is a deliberate edit of `ref`/`sha` (and `version`) in `.claude-plugin/marketplace.json`,
followed by `make verify-structure`. See [`specs/claude-git-pr-skill.md`](specs/claude-git-pr-skill.md)
for the procedure.

## Tagging a repo release (optional)

If you cut GitHub releases for the marketplace as a whole, use a `v`-prefixed semver tag (e.g.
`v0.2.0`) that matches the marketplace `metadata.version`, and let `make changelog` populate the
release notes from the conventional commits since the last tag.
