# License and Third-Party Attributions

The `meta-docs` plugin is distributed under the MIT License for original plugin scaffolding,
documentation, subagent definitions, and the adapted `unslop` and `interrogate` skills, and includes
`humanize-skills` under the Creative Commons Attribution 4.0 International Public License (CC BY
4.0).

## 1. `humanize-skills` (CC BY 4.0)

- **Component**: `skills/humanize-skills/`
- **Copyright**: © Adem Kurtipek (`https://github.com/gencharitaci/humanize-skills`)
- **License**: Creative Commons Attribution 4.0 International Public License (CC BY 4.0)
  (`https://creativecommons.org/licenses/by/4.0/`)
- **Modifications**: Packaged inside `plugins/meta/meta-docs/skills/humanize-skills/` for the
  `boss-skills` marketplace (ported from the `meta-docs` plugin in
  `Adobe-AIFoundations/aif-skills`); markdown formatting and relative reference links validated
  for cross-runtime compatibility; an `## Examples` section of invocation commands added to
  `SKILL.md`.

## 2. `unslop` and `interrogate` (MIT)

- **Components**: `skills/unslop/` and `skills/interrogate/`
- **Upstream Source**: Adapted from `pstack` by Lauren Tan in
  `https://github.com/cursor/plugins/tree/main/pstack/skills`
- **Additional Workflow Guidance**: Incorporates separate-pass anti-slop review practices described
  by Flavio Copes (`https://flaviocopes.com/anti-slop/` and `https://flaviocopes.com/unslop/`).
- **Modifications**: Enabled autonomous model and subagent invocation alongside explicit slash
  invocation, added the separate review pass workflow and playbook reference to `unslop`, and
  inlined self-contained framing, multi-runner worktree fan-out, and verification phases into
  `interrogate`.
