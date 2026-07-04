# PluginEval Reports

Generated [wshobson PluginEval](https://github.com/wshobson/agents/tree/main/plugins/plugin-eval)
quality reports for this repo's skills, one Markdown file per skill. They are produced by the
[`/skill-evals`](../../.claude/skills/skill-evals/SKILL.md) skill / `make eval-skill` and are
**regenerated output** — overwrite freely.

These live here, under `docs/evals/`, rather than inside each skill directory: an eval report is
process/meta documentation, not content an agent needs to do the job, so keeping it out of the
skill folder keeps the skill tree limited to `SKILL.md` + `references/` + `scripts/`.

**Path convention:** `docs/evals/<plugin>/<skill>.md` for plugin skills (and
`docs/evals/<skill>.md` for repo-internal `.claude/skills/<skill>`).

## agent-harness

### PR-review family

- [fetch-diff](agent-harness/fetch-diff.md)
- [add-review-comment](agent-harness/add-review-comment.md)
- [pr-review](agent-harness/pr-review.md)
- [fetch-unresolved-comments](agent-harness/fetch-unresolved-comments.md)

### Worktree lifecycle suite

- [git-worktree](agent-harness/git-worktree.md)
- [git-worktree-clean](agent-harness/git-worktree-clean.md)
- [git-worktree-remove](agent-harness/git-worktree-remove.md)
- [git-worktree-status](agent-harness/git-worktree-status.md)
- [worktree-doctor](agent-harness/worktree-doctor.md)

### Other

- [pyrefly-typing](agent-harness/pyrefly-typing.md)
- [release-notes-generator](agent-harness/release-notes-generator.md)
- [stop-slop](agent-harness/stop-slop.md)
- [unicode-hygiene](agent-harness/unicode-hygiene.md)
