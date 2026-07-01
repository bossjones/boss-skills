# Rubric map

Pick the rule files to read based on what the target actually contains. Reading every rule for
every review is wasteful and dilutes focus — map the languages and concerns present in the
in-scope code to the specific `.cursor/rules/security-*.mdc` files below.

`security-global-base.mdc` **always applies** (it is the repo's always-on baseline: defense in
depth, least privilege, fail securely, secure by default, plus 9 critical rules and the mandate
that every violation cite the rule it triggered).

## By language

| Target contains | Read |
| --------------- | ---- |
| Python (`**/*.py`, `**/*.ipynb`, `**/*.pyw`) | `security-lang/security-lang-python.mdc` (16 numbered Python rules: input validation, no user input in paths, parameterized queries, no `eval`/`exec`, `hmac.compare_digest`, safe subprocess/no `shell=True`, output escaping, no hardcoded secrets, restricted dynamic imports, no `pickle` on untrusted data, `yaml.safe_load`, keep framework defaults, dep hygiene) |
| Other languages (JS/TS, PHP, Go, …) | No language-specific file exists yet; apply the global rules below. Many global files include JavaScript/PHP unsafe-vs-safe examples. |

## By concern

Match the security-relevant surfaces you find during recon to these global rules:

| Concern seen in code | Read (`security-global/…`) |
| -------------------- | -------------------------- |
| Untrusted input reaching a dangerous sink (shell, FS, DB, template, eval, network) | `security-global-dangerous-flows.mdc` (taint-tracing playbook), `security-global-input-validation.mdc` |
| SQL / query construction | `security-global-sql-usage.mdc`, `security-global-injection-prevention.mdc` |
| Command / OS execution, subprocess | `security-global-injection-prevention.mdc`, `security-global-dangerous-flows.mdc` |
| File paths, uploads, archive extraction | `security-global-pathtraversal-prevention.mdc` |
| Outbound HTTP / user-supplied URLs / webhooks | `security-global-ssrf-prevention.mdc` |
| XML parsing | `security-global-xxe-prevention.mdc` |
| Rendering user data into HTML/JS/CSS/URL/SQL/shell/LDAP/JSON | `security-global-output-encoding.mdc` |
| Login, sessions, passwords, tokens, RBAC/ABAC | `security-global-auth.mdc` |
| HTTP API surface (versioning, auth, rate limits, CORS, headers) | `security-global-api.mdc` |
| Secrets, keys, credentials, config, containers, IaC | `security-global-secure-configuration.mdc`, `security-global-data-protection.mdc` |
| Encryption, TLS, key management, PII handling | `security-global-data-protection.mdc` |
| Error handling, logging, security monitoring | `security-global-error-handling.mdc` |
| Dependencies, lockfiles, supply chain | `security-global-dependency-mgmt.mdc`, `security-global-snyk.mdc` |
| MCP servers, tools, agent-invoked commands/file edits | `security-global-mcp-usage.mdc` |

Read only what matches. A small Python diff that touches a subprocess call needs `base` +
`security-lang-python.mdc` + `injection-prevention.mdc` + `dangerous-flows.mdc` — not all 18.

## Citing a rule in a finding

The rule files use two conventions you can cite precisely:
- The numbered-rule files (`base`, `sql-usage`, `python`, `ssrf`, `xxe`, `path-traversal`,
  `dangerous-flows`) use `## N. Rule Title` with a bold `**Rule:**`. Cite as
  `security-lang-python.mdc rule 7 (Safe Subprocess Usage)`.
- The prose/checklist files end with an "Anti-Patterns to Avoid" list. Cite the file and the
  specific anti-pattern.

## Fallback checklist (when `.cursor/rules/` is absent)

If the repo has no `.cursor/rules/` directory, review against this OWASP-style checklist instead
and cite OWASP/CWE in findings. Note the fallback in the report's Notes section.

- **Injection** — SQL/NoSQL/command/LDAP/XPath built from untrusted input without
  parameterization or safe APIs (CWE-89, CWE-78).
- **Broken auth / session** — weak password storage, missing MFA, predictable/long-lived tokens,
  missing authz checks, IDOR (CWE-287, CWE-639).
- **Sensitive data exposure** — hardcoded secrets, secrets in logs, missing encryption in
  transit/at rest, PII overexposure (CWE-798, CWE-312, CWE-532).
- **XXE / unsafe deserialization** — DTD/external entities enabled, `pickle`/`yaml.load`/native
  deserialization on untrusted data (CWE-611, CWE-502).
- **Broken access control** — client-side-only enforcement, missing server-side authz, path
  traversal, SSRF to internal ranges (CWE-22, CWE-918, CWE-284).
- **Security misconfiguration** — insecure defaults, disabled framework protections (CSRF/CORS/
  auto-escaping), verbose errors leaking internals (CWE-16).
- **Vulnerable dependencies** — unpinned/outdated packages, no lockfile, no vuln scanning
  (CWE-1104, CWE-937).
- **Dynamic code execution** — `eval`/`exec`/`compile`/dynamic import on attacker-influenced
  input (CWE-95).
- **Insufficient logging/monitoring** — no audit trail for security events, or logging that
  itself leaks secrets (CWE-778).
