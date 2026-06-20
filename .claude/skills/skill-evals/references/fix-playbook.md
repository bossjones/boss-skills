# Fix playbook — weak dimension → concrete SKILL.md remedy

Used by the `--fix` path. Read the skill's report under `docs/evals/` (see the Report
location convention in `../SKILL.md`), sort dimensions ascending, and start
with the lowest. Each remedy below is a starting point, not a checklist to apply blindly —
cross-check against `agent-skills-how-skills-work.md` and keep edits principled (explain the
*why*, generalize, don't overfit to the metric).

## Static dimensions

| Weak dimension | Likely cause | Remedy |
|----------------|--------------|--------|
| `frontmatter_quality` | Vague description, weak/missing triggers | Tighten the `description`: add concrete "Use when …" triggers and the specific contexts/phrases that should activate it. Keep under 1024 chars. |
| `progressive_disclosure` | Too much (or too little) in the SKILL.md body | If the body is bloated, move detail into focused `references/` files and link them. If the skill is a thin stub, ensure the body actually covers the workflow. Aim for the 200–600 line sweet spot. |
| `orchestration_wiring` | No documented inputs/outputs or examples | Document what the skill consumes and produces; add concrete command/example blocks; ensure it reads as a worker, not a vague orchestrator. |
| `structural_completeness` | Missing examples/troubleshooting, low heading density | Add an Examples section, a Troubleshooting/Notes section, and clear headings. |
| `token_efficiency` | Duplicated lines, MUST/NEVER overuse | Remove duplication; replace rigid directives with reasoned prose. |
| `ecosystem_coherence` | No links to sibling skills/agents | Add "see also" / cross-references to related skills where genuinely relevant. |
| `harness_portability` | Tool/model refs that don't port across harnesses | Speak in actions over tool names; avoid name collisions and hard-coded model aliases. |

## Judge dimensions

| Weak dimension | Remedy |
|----------------|--------|
| `triggering_accuracy` | Improve the `description` so should-trigger vs should-not-trigger prompts separate cleanly — add the near-miss contexts that belong, exclude adjacent ones that don't. |
| `orchestration_fitness` | Clarify the skill's role and the concrete steps it performs. |
| `output_quality` | Make the expected output format explicit (template/structure) so runs are consistent. |
| `scope_calibration` | Right-size the scope — neither a kitchen-sink skill nor an over-narrow one-off. |

## Script-backed skills (Robustness / Code Template Quality reading 0)

When a skill's real logic lives in `scripts/` (as the git-worktree skills do), the static
layer — which reads the SKILL.md — can score code-quality dimensions at 0 even though the
scripts are fine. Don't paste code into the SKILL.md to game this. Instead ensure the body
clearly references the scripts, documents their inputs/outputs and failure modes, and shows
example invocations. The honest fix is documentation quality, not inlining code.

After editing, re-run `make eval-skill SKILL=<path>`, overwrite the `docs/evals/` report, and record the
before→after composite score. Leave edits uncommitted for the user to review.
