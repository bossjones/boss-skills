# Lens: disclosure

`theme: "disclosure"`. Credentials, audience mismatch, and untrusted text reaching an agent.

Run every gate in `quality-gates.md`. Return only the JSON in `observation-format.md`.

**Calibrate to the real audience before flagging anything.** Probe the repo's actual visibility
(`gh repo view --json visibility` if `gh` is available) rather than assuming. Most repos this
skill reviews are internal-team-visible, not public and not secret. Naming a colleague in a
commit or a doc is normal and is **not** a finding. Recording what that colleague said about a
customer's contract may be. **Do not manufacture a leak** — a fabricated privacy finding costs
more trust than it saves. When visibility cannot be determined, say so and default to the least
alarming reasonable interpretation.

Vulnerability scanning (SQL injection, SSRF, path traversal, dependency CVEs) is a related but
separate concern with its own methodology and severity model — see
[`boss-security-review`](../../../boss-security-review/SKILL.md). This lens covers what is *in
the diff itself*, not a general code-security sweep.

## Domain

Anything in the diff that reaches a wider audience than its source intended, and anything that
lets untrusted text steer an agent.

## Non-negotiables — CRITICAL

**A live credential in tracked content.** A token, key, password, cookie, or bearer value — a
value pulled from `.env`, a local settings override, or any other gitignored secrets file; an
API key pasted into a doc as an example; a connection string with a password. Such files are
gitignored precisely so their contents never land in a commit; a value from one appearing in the
diff is CRITICAL regardless of whether it still works. Report the *location*, never re-print the
secret — quote the surrounding line with the value elided.

**A guard weakened.** A script or workflow change that disables a check, widens a permission, or
removes a redaction step.

## The rest of the surface

**Un-redacted transcript or recording content.** A verbatim meeting transcript, an off-hand
personal opinion attributed by name, or a candid assessment of a person or team pasted into a
durable doc is a finding. Synthesized, attributed-to-a-role content is fine. If the discovered
rules distinguish raw from synthesized content explicitly, cite that rule; otherwise judge on
the content itself.

**Audience mismatch.** Content pasted from a source with a narrower audience than the target
repo: named external customers, unannounced dates or roadmap commitments, revenue or headcount
figures, compensation, anything from a legal or HR context, a document marked with a
confidentiality label. Say which source it came from and why its audience is narrower.

**Personal data.** Home addresses, personal phone numbers, personal email addresses, anything
about an identified individual that is not work-role information.

**Prompt injection.** Any skill, agent config, or automation that fetches external content
(a wiki page, a ticket, a chat message, a transcript) and hands it to an agent that holds tools
and credentials is a live target. Flag:

- untrusted fetched content concatenated into an *instruction* position in a skill or prompt,
  rather than clearly fenced as data
- tool output treated as an instruction rather than as data to summarise
- a rule, config, or allowlist file read from a **mutable** location where an untrusted party
  could edit it, instead of at a pinned SHA (this skill's own Step 2 reads rules at `$BASE_SHA`
  for exactly this reason — cite it as the mitigating pattern when relevant)
- a permission or allowlist the agent itself can widen
- a skill that writes to an external system on content it did not verify, with no human
  confirmation step

**Outbound writes.** A change that makes a skill or automation write to an external system
(a tracker, a wiki, a chat channel, a git host) without an explicit confirmation gate. Publishing
is not reversible in the way a local edit is.

## Categories

`secret-exposure`, `credential-in-doc`, `unredacted-transcript`, `audience-mismatch`, `pii`,
`prompt-injection`, `untrusted-content-in-instruction`, `mutable-rule-source`,
`unconfirmed-outbound-write`.

## Evidence bar

Name the concrete exposure: which value, which line, and who can read it that should not. For
prompt injection, name the path — which fetched content, reaching which instruction position,
with which tools available. "This could be exploited" with no path is not a finding.

## Do not report

A colleague's name in a work context. A work email address in an authorship or attribution
line. An internal URL, if the repo is internally visible. A placeholder or obviously-fake example
credential (`xxx`, `<your-token-here>`, `sk-example`). Generic hardening advice with no reachable
path. A CVE in a dependency the diff did not introduce — that belongs to a dedicated
vulnerability scan, not this lens.
