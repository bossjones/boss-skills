# Tutorials

Hands-on, task-first walkthroughs for the plugins published by the `boss-skills` marketplace.

Where the [plugin reference pages](../plugins/README.md) describe *what each plugin is* — its
components, options, and install commands — these tutorials show *how to actually use one* end to
end: prerequisites, the exact prompts to type, and what to expect at each step.

For repo-level setup and the development workflow, see the [root README](../../README.md).

## Available tutorials

Tutorials are organized **one folder per plugin**, so a plugin can grow from a single walkthrough
into a numbered series with bundled screenshots over time.

| Plugin | Tutorial | What you'll do |
|--------|----------|----------------|
| [agent-harness](agent-harness/README.md) | [Ship a feature with the agent-harness loop](agent-harness/README.md) | Run plan → worktree → autobuild → PR → address review, end to end |
| [agent-harness](agent-harness/README.md) | [Set up your second brain](agent-harness/second-brain.md) | Install obsidian-wiki + optional QMD semantic search via the setup-second-brain skill |
| [github-pr-review](github-pr-review/README.md) | [Review your first PR](github-pr-review/README.md) | Install the plugin and post an approval-gated PR review with inline code suggestions |
| [python-dev](python-dev/README.md) | [Get a red CI run green, then ship the fix](python-dev/README.md) | Debug a failed GitHub Actions run and open a conventional-commit PR |
| [twitter-tools](twitter-tools/README.md) | [From tweet to Instagram Reel](twitter-tools/README.md) | Download tweet media and compose a 9:16 vertical Reel |
| [proxmox-infra](proxmox-infra/README.md) | [Provision a Proxmox VM from a cloud-init template](proxmox-infra/README.md) | Clone a template into a running VM, then verify cluster health |

## Adding a tutorial

When you write a tutorial for another plugin, follow this convention so the tree stays predictable:

```text
docs/tutorials/
├── README.md                 # this index — add a row to the table above
└── <plugin-name>/            # one folder per plugin (kebab-case, matches the plugin name)
    ├── README.md             # the landing walkthrough (start here)
    ├── 01-*.md, 02-*.md      # optional: numbered parts for a multi-step series
    └── assets/               # optional: screenshots and sample files
```

- Use kebab-case folder and file names, matching the
  [documentation conventions](../../.claude/rules/documentation.md).
- Cross-link the tutorial to its [reference page](../plugins/README.md) and back.
- Keep prompts and commands accurate — verify them against the plugin's reference page (and its
  upstream source, for external plugins) before publishing.
