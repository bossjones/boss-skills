# skillgrade bootstrap demo (`skillgrade init`)

A record of validating the `skillgrade` CLI against this plugin's `claude-config-validation`
skill. **Takeaway: the toolchain works** (install, run, scaffold, graders); the **AI-powered**
eval generation in skillgrade `0.1.6` currently fails with an Anthropic `404` and falls back to
a template — so the **committed, hand-ported `eval/eval.yaml` remains the source of truth**.

## What was run

Against a throwaway copy of the skill's `SKILL.md` (so it could not clobber the committed
`skills/claude-config-validation/eval/`):

```bash
# template mode (no key) — succeeds, writes a commented template
npx --yes skillgrade@latest init

# AI mode (with an Anthropic key) — attempted
source .env && ANTHROPIC_API_KEY="${BOSS_ANTHROPIC_API_KEY}" npx --yes skillgrade@latest init
```

## Observed output

```
skillgrade init
  Found 1 skill(s): claude-config-validation
    init   generating eval with Anthropic
    init   AI generation failed: Anthropic API returned 404
     Falling back to template.
  Created eval.yaml.
```

- `npx skillgrade@latest --version` → `0.1.6` (installs and runs fine under Node 20).
- Template-mode `init` → writes a valid `eval.yaml` template.
- AI-mode `init` → **`Anthropic API returned 404`**, then template fallback. A `404` here means
  the model identifier skillgrade `0.1.6` requests does not resolve for the account. `init`
  exposes **no `--model` override**, so this cannot be worked around from the CLI. This is a
  skillgrade-version limitation, independent of this plugin. Re-try after a skillgrade release
  that targets a current model, or author the `eval.yaml` by hand (recommended — see below).

## The template `init` produces

```yaml
version: "1"
defaults:
  agent: gemini          # gemini | claude
  provider: docker       # docker | local (use local for quick iteration)
  trials: 5
  timeout: 300
  threshold: 0.8
tasks:
  - name: test-claude-config-validation
    instruction: |
      TODO: Write an instruction based on this skill.
    graders:
      - type: deterministic
        run: |
          echo '{"score": 0.0, "details": "TODO: implement grader"}'
        weight: 0.7
      - type: llm_rubric
        rubric: |
          # TODO: Write a rubric for the LLM grader.
        weight: 0.3
```

> Note the upstream defaults are `agent: gemini` / `provider: docker`. This plugin's hand-crafted
> evals deliberately pin `agent: claude` / `provider: local` for keyless local iteration via
> `/run-skill-eval`.

## The real, working eval suite

The committed, proven suite lives at
[`skills/claude-config-validation/eval/`](../skills/claude-config-validation/eval/): a filled-in
`eval.yaml`, four zero-dependency Node graders, and 13 positive/negative fixtures — ported and
genericized from a battle-tested source. Run it two ways:

```bash
# local (Claude Code is the agent, no key, no Docker)
/run-skill-eval plugins/boss-experimental/boss-experimental/skills/claude-config-validation

# CI (real skillgrade trials; needs a resolvable model + ANTHROPIC_API_KEY)
cd plugins/boss-experimental/boss-experimental/skills/claude-config-validation/eval
./run_eval.sh --smoke --provider=local
```

For a brand-new skill, `skillgrade init` (template mode) plus `/scaffold-skill-eval` is the
fastest way to a first `eval/`; fill in real `instruction`s, `workspace` fixtures, and graders
following the schema in [`skillgrade-eval-yaml-schema.md`](skillgrade-eval-yaml-schema.md).
