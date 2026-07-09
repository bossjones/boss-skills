# Configuration

`claude-config-validation`'s `SKILL.md` explicitly calls out two constants as **config-driven,
not hardcoded** — a repo is expected to override them rather than treat them as fixed
requirements. It also documents two **opt-in extension points**: Check 22 (skill eval coverage)
and the pipeline-declaration mechanism for custom agents.

The plugin's other configurable surface is the **skillgrade model** used by the eval system;
[Selecting the skillgrade model](#selecting-the-skillgrade-model) below covers it.

## Selecting the skillgrade model

The LLM model used by `skillgrade` — both the `llm_rubric` grader and AI-mode `skillgrade init` —
is configurable, so **adopting a newly released model never requires a code change or a plugin PR**.

**LLM grader** (a `skillgrade` run), highest precedence first:

1. A grader's own `model:`
2. A task's `grader_model:`
3. `defaults.grader_model:` in `eval.yaml`
4. The provider's `*_MODEL` env var — `ANTHROPIC_MODEL`, `OPENAI_MODEL`, `GEMINI_MODEL`
5. The provider's built-in default (`anthropic` → `claude-sonnet-5`, `openai` → `gpt-4o`,
   `gemini` → `gemini-3-flash-preview`)

**`skillgrade init`** (AI scaffold — no config file exists yet): `*_MODEL` env var → provider default.

```yaml
# Pin the grader model in eval.yaml (upstream-safe):
defaults:
  grader_provider: anthropic
  grader_model: claude-sonnet-5     # or any current model ID
```

```bash
# Or override a single run without editing any file:
ANTHROPIC_MODEL=claude-opus-4-8 skillgrade
```

> **skillgrade version note:** The `defaults.grader_model` / per-task `grader_model` / per-grader
> `model:` config fields work on upstream skillgrade today. The `ANTHROPIC_MODEL` / `OPENAI_MODEL`
> / `GEMINI_MODEL` environment-variable override — and the fix for the `skillgrade init` AI-mode
> 404 — currently live only in the `bossjones/skillgrade` fork (branch
> `fix/anthropic-retired-model-404`) and require that fork or a future upstream release. With
> upstream `npx skillgrade@latest`, if `init` returns 404 use template mode or `/scaffold-skill-eval`.

Full field reference: [`references/skillgrade-eval-yaml-schema.md`](../references/skillgrade-eval-yaml-schema.md)
→ Model selection.

## Monorepo-root markers

Used in Step 0 of `claude-config-validation` to decide whether the current directory *is* the
monorepo root (and therefore should not be silently auto-validated without an explicit
`project_path`).

**Default marker set** (any one is sufficient):

- a `.git` directory
- `pnpm-workspace.yaml`
- a `package.json` whose top-level object has a `workspaces` field
- `lerna.json`
- `nx.json`

**Override**: a repo using different tooling (a Python monorepo, a Cargo or Go workspace, etc.) is
expected to adjust this set — e.g. in its own copy of the skill, or documented in a `CLAUDE.md`
note the skill's operator reads before running the check. The skill's `SKILL.md` frames this
plainly: "Adjust to match the repo's tooling."

## Canonical agent roles

Used in Check 2 ("Canonical agents") to decide which agent names are root-owned and therefore
must not be redefined by a config home.

**Default set**: `architect`, `coder`, `test-writer`, `tester`, `reviewer`, `pr-submission`,
`learner` — exactly the seven non-governance agents shipped under [`agents/`](../agents/) in
this plugin (the eighth, `config-reviewer`, is a *governance* agent and is explicitly excluded
from the standard set per the knowledge-architecture doctrine).

**This is a recommended default, not a hard requirement.** A repo may declare its own role list
— fewer, more, or differently named roles — and the skill validates against *whatever set the
repo declares*, falling back to the default only when none is declared.

**What the check actually enforces**, once the set is known:

- **At a config home**: no agent may reuse a canonical role name (a same-named override is
  silently shadowed by the root agent and never runs — FAIL), and no agent may be a renamed
  canonical role (e.g. `implementer.md` standing in for `coder` — FAIL) or a canonical
  platform-variant (`coder-mobile.md` — FAIL).
- **At the root**: every declared canonical role must be present, with role-appropriate
  frontmatter (a read-only role like `tester` or `reviewer` must not request write tools —
  FAIL if it does).

### The pipeline-declared-agent extension point

A config home *is* allowed to define a **domain-prefixed** custom agent (e.g. `myapp-coder`) —
but only conditionally, and this is where the extension point lives.

**Default convention**: a `.claude/pipelines.json` file listing pipelines and the agents each
pipeline phase invokes. Example, from the shipped `custom-pipeline-agent` fixture
([`skills/claude-config-validation/eval/test-fixtures/custom-pipeline-agent/.claude/pipelines.json`](../skills/claude-config-validation/eval/test-fixtures/custom-pipeline-agent/.claude/pipelines.json)):

```json
{
    "pipelines": [
        {
            "id": "custom-pipeline",
            "phases": [
                {
                    "id": "custom-code",
                    "agent": "example-coder"
                }
            ]
        }
    ]
}
```

**Decision logic the check applies:**

1. Does the project have a pipeline-declaration file (default: `.claude/pipelines.json`)?
   - **Yes** — read it. Is the custom agent's name referenced by some declared pipeline?
     - **Referenced** → WARN ("confirm intentional") — allowed, but flagged for human
       confirmation.
     - **Not referenced by any pipeline** → FAIL — a "stray fork" with no declared reason to
       exist.
   - **No** (the repo uses no pipeline mechanism at all) — treat *any* project-prefixed custom
     agent as WARN pending confirmation, since there's no declaration to check against.

This is explicitly framed as **optional and documented**, not a universal requirement — a repo
that never uses `.claude/pipelines.json` isn't penalized for lacking one; it just gets the
more conservative WARN treatment for any custom agent it does define.

## Check 22 (opt-in): skill eval coverage

Check 22 asks whether every skill under `.claude/skills/` has an `eval/` directory containing
`eval.yaml` — but it is explicitly **not a universal mandate**:

- **Repo has NOT opted into eval coverage** → Check 22 reports **N/A** for every skill. This is
  the default assumption.
- **Repo HAS opted in** →
  - `eval/` directory missing entirely → **FAIL**
  - `eval/` directory exists but `eval.yaml` is missing → **WARN**
  - `eval/` exists with `eval.yaml` → **PASS**

The knowledge-architecture doctrine's own "Eval" section reinforces the same opt-in framing:
apply eval coverage "where silent regressions would be costly (root-level skills, skills that
reference external docs)" — integration wrappers that just delegate to an MCP server typically
don't need one. There is no mechanism documented for *declaring* opt-in (unlike the
pipeline-declaration file for Check 2) — it is a judgment call the skill operator communicates
when invoking the check, or documents in the project's own `CLAUDE.md`.

## Where these constants live in practice

Neither constant is read from a config file by the skill itself — `claude-config-validation` has
no `Bash` access and reads no settings JSON for these values. Both are **documented defaults in
the `SKILL.md`'s "Configuration" section**, and overriding them means either (a) forking the
skill with a different default baked in, or (b) documenting the repo's actual set somewhere the
skill's human operator will read before invoking it (the `SKILL.md` suggests a `CLAUDE.md` note
as one option). This keeps the skill itself generic and portable across repos while still
letting each repo assert its own canonical set and monorepo tooling.
