# Severity model

Grade each finding by the **realistic impact of exploitation** and how **reachable** the flaw
is, not by how alarming the pattern looks in isolation. A dangerous function guarded by strict
validation and unreachable by untrusted input is not a Critical. Conversely, a "small" bug on a
direct untrusted-input path can be Critical. When in doubt between two levels, let reachability
decide: attacker-controlled and reachable pushes it up; defense-in-depth and hard-to-reach pushes
it down.

## Levels

- **Critical** — Direct, serious compromise with a realistic path to exploitation. Examples:
  remote code execution, authentication/authorization bypass, SQL injection returning or mutating
  data, a live/valid secret committed to the repo, unsafe deserialization of attacker-controlled
  input (`pickle.loads`, `yaml.load`). Fix before merge/release.
- **High** — Serious weakness that is exploitable but needs a condition (specific input, elevated
  position, or chaining). Examples: `subprocess(..., shell=True)` with partially-validated input,
  SSRF reachable but limited, path traversal on a non-critical resource, missing authz on a
  sensitive-but-not-catastrophic endpoint, weak password hashing (fast/unsalted). Fix promptly.
- **Medium** — Real issue with limited impact or meaningful mitigating factors. Examples: missing
  output encoding in a low-risk context, verbose error messages leaking stack traces, missing
  rate limiting, an unpinned dependency with no known-exploited CVE, secrets in logs at debug
  level. Fix in normal course.
- **Low** — Minor hardening gap or best-practice deviation with little standalone risk. Examples:
  missing security header, overly broad CORS on a non-sensitive route, a `# security-reviewed`
  annotation missing on an intentional exception. Address opportunistically.
- **Info** — Not a vulnerability; an observation, defense-in-depth suggestion, or note for the
  reviewer's awareness. No action required.

## Ordering the Immediate Remediation list

Include the `## Immediate Remediation` section only when at least one Critical or High finding
exists. Order it by: (1) severity (Critical before High), then (2) reachability from untrusted
input (directly reachable first), then (3) blast radius (broadest impact first). The goal is a
"do these first" list a developer can act on top-to-bottom before merging.

## Calibration reminders

- Do **not** inflate severity to make the report look thorough. A precise Medium is more useful
  than an exaggerated Critical.
- Do **not** hedge a genuine Critical into a Medium with caveats. Name it clearly and let the
  Remediation section carry the nuance.
- A clean review (zero findings) is a valid outcome — report it as such.
