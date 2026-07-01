---
name: boss-security-review
description: >
  Performs a security review / security audit / vulnerability review of code and writes a
  structured, severity-graded findings report (default path specs/security-review.md, overridable
  from the request). Reviews changed code by default; the request can override the target to a
  named path (e.g. "review src/auth/") or the whole repo. Reviews against a bundled security
  rubric (and the target repo's .cursor/rules/security-* rules when present) and cites the
  specific rule each finding triggered. Use whenever the user asks to "run a security review",
  "do a security audit", "audit this for vulnerabilities", "check for security issues", "review
  my changes for security", "is this code secure", "find security bugs", or "look for injection /
  SSRF / path traversal / hardcoded secrets" — including a pre-merge pass on a branch, PR, file,
  or directory. Prefer this over an ad-hoc review so findings are graded, cite the triggered rule,
  and land in a re-checkable report.
---

# Security Review

Review a `TARGET` against this repository's security rubric and write an actionable findings
report to `REPORT_OUTPUT_PATH`. Each finding names the exact rule it violates and why, is graded
by severity, and comes with a concrete fix and a way to confirm the fix. Work through the
`Instructions` and `Workflow` below, produce the report in the `Report Format`, then print the
`Report` summary.

This skill is **advisory** — it finds and documents problems. It does not modify the reviewed
code unless the request explicitly asks for fixes in the same turn.

## Variables

- **TARGET** — what to review. Derived from the user's request. Default (no explicit target):
  **changed code** = `git diff main...HEAD` plus uncommitted working-tree changes
  (`git status`, `git diff`, and `git diff --staged`). If the repo's default branch is not
  `main` (e.g. `master`/`trunk`), diff against the actual default branch instead. The request
  overrides this with a path (`review plugins/foo/`), a set of files, or `whole repo` (review
  the full tree).
- **REPORT_OUTPUT_PATH** — where the report is written. Default: `specs/security-review.md`.
  If the request names a different path (e.g. "write it to specs/auth-security.md"), use that.
- **RULES_SOURCE** — where the rubric is read from, resolved in this order (first that exists
  wins), per `references/rubric-map.md`:
  1. The **target repo's** `.cursor/rules/security-global/` + `.cursor/rules/security-lang/` — the
     repo's own live standard takes precedence when present.
  2. The **bundled** copy at `${CLAUDE_SKILL_DIR}/references/security-rules/` — verbatim rule
     files shipped with this skill, so it works in any repo.
  3. The built-in **OWASP/CWE fallback** checklist at the bottom of `references/rubric-map.md`.

  Note in the report's Notes which source was used.

## Instructions

- **Resolve the target first.** Determine concretely which files/lines are in scope before
  reviewing anything. If the request is ambiguous about scope, state the chosen interpretation
  in the report's Scope section rather than stalling.
- **Load only the relevant rubric.** Do not read all 18 rule files every time. Use
  `references/rubric-map.md` to resolve the rubric source (target repo's `.cursor/rules/` if
  present, else the bundled copies) and to map the languages and concerns present in the target
  to the specific `security-*.mdc` files worth reading. `security-global-base.mdc` always applies.
- **Cite the triggered rule for every finding.** State which rule fired and *why* it applies to
  this code. This is not optional decoration — the base rule mandates it: "All violations must
  include a clear explanation of which rule was triggered and why." A finding without a cited
  rule (or a clearly-stated OWASP/CWE basis when using the fallback checklist) is incomplete.
- **Do not invent findings.** A clean review is a valid, expected result. If the target has no
  security issues, say so plainly and emit a zero-finding report. Never manufacture speculative
  problems to fill the report — false positives waste the reader's time and erode trust.
- **Grade honestly.** Classify each finding by severity (Critical/High/Medium/Low/Info) and a
  category (injection, authz, secrets, crypto, SSRF, path-traversal, deps, config, logging,
  MCP/agent, …). See `references/severity-model.md`. Reserve Critical/High for real,
  reachable impact — don't inflate severity, and don't bury a genuine Critical under caveats.
- **Scale the effort to the target.** For a small target, review directly in this context. For a
  large diff or a whole-repo audit, fan out parallel review subagents and merge their findings —
  see `references/fanout.md`.
- **Graceful fallback.** If neither the target repo's `.cursor/rules/` nor the bundled
  `references/security-rules/` copies are available, fall back to the built-in OWASP-style
  checklist at the bottom of `references/rubric-map.md`, and note in the report's Notes section
  that the structured rubric was unavailable.

## Workflow

1. **Resolve Target** — Determine the exact files/lines in scope (default: changed code). Use
   `git diff main...HEAD`, `git status`, and `git diff` for the changed-code default; use the
   named path or full tree when the request overrides.
2. **Load Rubric** — From the target's languages and apparent concerns, pick the rule files to
   read via `references/rubric-map.md`. Always include `security-global-base.mdc`.
3. **Recon & Classify** — Skim the in-scope code to identify languages, entry points, trust
   boundaries, and the security-relevant surfaces present (user input → dangerous sinks,
   auth/session, secrets/config, external calls, deserialization, SQL, XML, subprocess, etc.).
4. **Analyze** — Review the code against the loaded rules. Decide single-context vs. fan-out per
   `references/fanout.md`; when fanning out, give each subagent its file subset and the rule
   files it must apply, and collect their findings.
5. **Triage & Dedupe** — Merge findings, remove duplicates (same `file:line` + same rule), and
   assign final severity + category to each.
6. **Document** — Write the report to `REPORT_OUTPUT_PATH` using the `Report Format` exactly.
   Create parent directories if needed.
7. **Save & Report** — Confirm the file was written and print the `Report` summary block.

## Report Format

Write the report in this structure. Omit the per-finding block entirely when there are no
findings (keep the Summary table with zero counts and state "No findings" under Findings).

```md
# Security Review: <target>

## Scope
- Target: <what was reviewed — diff range, path(s), or "whole repo">
- Ref: <branch / commit reviewed>
- Rubric source: <live .cursor/rules/ | bundled security-rules | OWASP fallback>  (<rule files actually applied>)
- Date: <YYYY-MM-DD>

## Summary
| Severity | Count |
| -------- | ----- |
| Critical | <n>   |
| High     | <n>   |
| Medium   | <n>   |
| Low      | <n>   |
| Info     | <n>   |

Top risks:
- <one-line summary of the highest-impact issue, or "None — no findings">

<!-- Include this section only if there is at least one Critical or High finding: -->
## Immediate Remediation
1. <do this first — highest severity, most reachable>
2. <next>

## Findings

<!-- One block per finding, ordered by severity (Critical first). If none: "No findings." -->
### [SEVERITY] <short title>  (<category>)
- Rule triggered: <which .cursor rule fired — e.g. security-lang-python.mdc rule 7 — and why it applies here>
- Location: <file:line (range)>
- Description: <what is wrong, concretely>
- Impact: <what an attacker gains / what breaks>
- Remediation: <the concrete fix; include a short safe-pattern snippet where it clarifies>
- References: <rule id / OWASP / CWE>

## Re-check
<how to confirm each finding is resolved — commands to run, or what to look for after the fix>

## Acceptance Criteria
<measurable definition of "all resolved" for this review>

## Notes
<assumptions made, areas explicitly out of scope, and — if applicable — that the structured
rubric was unavailable and the OWASP fallback checklist was used>
```

## Report

After writing the file, print this summary to the user (not into the report file):

```
✅ Security Review Complete
File: <REPORT_OUTPUT_PATH>
Target: <what was reviewed>
Findings: <c> critical, <h> high, <m> medium, <l> low, <i> info
Top risks:
- <risk 1>
- <risk 2>
```

## Reference Files

- `references/rubric-map.md` — Consult in Workflow step 2 to resolve the rubric source (live vs.
  bundled) and choose which `security-*.mdc` files to read for the target's languages and
  concerns. Also holds the OWASP-style fallback checklist for when no structured rubric is found.
- `references/security-rules/` — The bundled verbatim rubric (18 `.mdc` files). Read the specific
  files `rubric-map.md` points to; used when the target repo has no `.cursor/rules/`.
- `references/severity-model.md` — Consult in Workflow step 5 to assign severity consistently and
  to order the Immediate Remediation list.
- `references/fanout.md` — Consult in Workflow step 4 to decide single-context vs. parallel
  subagents and how to scope each subagent and merge its findings.

## When to invoke

- The user asks to review, audit, or check code for security issues, vulnerabilities, or a
  specific vuln class (injection, SSRF, path traversal, XXE, hardcoded secrets, unsafe
  deserialization, `shell=True`, etc.).
- The user wants a security pass on a branch, PR, file, or directory — especially "before I
  merge" — and wants the result written down rather than delivered as ephemeral chat.
- The user asks "is this secure?" about specific code in this repo.
