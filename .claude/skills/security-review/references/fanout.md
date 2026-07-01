# Adaptive fan-out

Scale the review effort to the size of the target. Reviewing a three-file diff with a fleet of
subagents wastes tokens and latency; reviewing a whole repo in one context risks shallow coverage
and missed files. Choose per the heuristic below.

## When to stay single-context

Review directly in the current context (no subagents) when the target is small enough to hold and
reason about carefully — roughly:
- a diff touching up to ~two dozen files, or
- a single file or a small directory, or
- any target where one pass can genuinely cover every in-scope line.

This is the common case for the default "changed code" target. Read the files, apply the loaded
rules, and write findings directly.

## When to fan out

Fan out to parallel review subagents when the target is large enough that one context would
skim — a big diff, a multi-package change, or a `whole repo` audit. Split the work one of two
ways (pick whichever gives cleaner, non-overlapping coverage):

- **By area** — one subagent per top-level directory / package / service. Best when the codebase
  is naturally partitioned and each part has a distinct security surface.
- **By concern** — one subagent per rule-category (injection, authz, secrets/config, SSRF/network,
  deserialization/deps, …), each scanning the whole target through one lens. Best when a single
  vuln class could hide anywhere and you want a thorough single-lens sweep.

For a large multi-language repo, a hybrid works: split by area first, and let each area's subagent
apply the concern rules relevant to its languages.

## Subagent contract

Give each review subagent:
- **Its file subset** — the exact paths (or diff hunks) it owns. Subsets should not overlap under
  by-area; under by-concern they cover the same files but each reports only its concern.
- **The rule files it must apply** — the relevant `.cursor/rules/security-*.mdc` paths from
  `rubric-map.md` (always including `security-global-base.mdc`).
- **The output shape** — findings in the per-finding block from the SKILL.md Report Format
  (severity, category, rule triggered + why, location `file:line`, description, impact,
  remediation, references). Instruct it to return raw findings only — no prose preamble — and to
  return an explicit "no findings" when its subset is clean.

Keep subagents **read-only**: they analyze and report; they do not edit code or write the report.

## Merging in the main context

After subagents return:
1. **Collect** all findings into one list.
2. **Dedupe** by `file:line` + triggered rule — the same issue can surface from two subagents
   (e.g. a by-area and a by-concern pass overlapping). Keep the clearer write-up; merge evidence.
3. **Re-triage** — assign final severity with `severity-model.md` applied consistently across the
   whole set, so two subagents don't grade the same class of bug differently.
4. **Order** findings by severity (Critical first) and build the Summary counts and Top risks.
5. Write the single report to `REPORT_OUTPUT_PATH`.

The main context owns severity consistency, deduplication, and the final report — subagents only
supply raw findings.
