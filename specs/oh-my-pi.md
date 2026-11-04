# oh-my-pi setup specification for macOS and Linux

Status: proposed configuration, pending approval. This document does not authorize installation, OAuth login, secret access, or changes to this machine.

Sequential re-review: Gemini 4 Argon reported no issues. Opus 5.5 identified a profile-selection gap plus approval ergonomics, writer-isolation, project-override, authorization-evidence, and provisioning concerns. This revision addresses those findings against the pinned source. Its task approval formatter does not show isolation flags, so writer approval requires a stronger inspection step than relying on the prompt summary. These reviews do not replace the implementation acceptance checks.

Research date: 2026-11-03. Fork source baseline: [`can1357/oh-my-pi` at `594670d6`](https://github.com/can1357/oh-my-pi/tree/594670d6b0b6d5f8080693aad34dedd38b5ebd94), whose CLI package declares version `18.16.0`. Pi's `/docs/latest` and catalogs are rolling references. Recheck the selected release and its configuration schema before implementing.

Public ecosystem follow-up: 2026-11-04. The user selected the public marketplace/plugin and standalone-skill adoption described in section 15, after core setup succeeds. Exclude Adobe-owned or Adobe-specific components and keep standalone skills as the final installation stage. This selection updates the spec's scope; it does not authorize installing anything on this machine.

## 1. Recommendation and scope

Configure **oh-my-pi (`omp`) as a batteries-included harness**, using its native tools before considering extensions. It already supplies subagents, Agent Hub, advisor reviews, planning/review surfaces, code intelligence, web access, browser/computer capabilities, memory integrations, and compatibility discovery. The initial work is choosing models, enabling the right bundled features, and controlling their permissions and data flows.

The requested account inventory is:

| Service | Available access | Intended use |
|---|---|---|
| Gemini | OAuth | Interactive work, research, independent review, supported native search |
| Anthropic | OAuth | Interactive work and independent review, subject to provider authorization |
| OpenAI Codex | OAuth | Coding and interactive work through the subscription backend |
| Tavily | `TAVILY_API_KEY` | Built-in web search |
| Firecrawl | `FIRECRAWL_API_KEY`, with a documented keyless search path | Search and authenticated extraction when needed |
| Brave | `BRAVE_API_KEY` | Built-in web search |

These are capabilities the user has, not evidence that credentials are present in this process or that a particular subscription permits a third-party client. **Current first-party Anthropic and Google documentation restricts the requested subscription-OAuth use in third-party harnesses.** Section 6 records those constraints; the setup must not treat a successful login as authorization.

**Resulting baseline: Codex-only chat inside OMP, subject to confirming its authorization.** Keep Claude and Gemini subscription use in their first-party tools. Adding those model families inside OMP requires a separately authorized access method, such as a Console/API or supported cloud-provider route, and approval of its billing. Cross-family advisor review therefore stays off in the baseline. This differs from the requested three-OAuth-provider outcome and needs the user's decision, not an assumption.

Deliver a reproducible macOS/Linux setup with explicit model roles, search routing, instruction/skill discovery, terminal behavior, approvals, and recovery procedures. Retain the existing Claude Code, Codex, and Copilot environments. Do not copy their credential stores, replace their executables, import all historical sessions, or install a second set of tools that duplicates OMP's built-ins.

**The selected public ecosystem is user-requested scope; implementation defaults remain proposals.** Unanswered decisions remain in section 13. Implementation must wait for approval of this spec.

## 2. Keep Pi and OMP separate

The supplied Pi documentation explains the upstream concepts. OMP's README, docs, and implementation define the setup contract for this spec.

| Area | Upstream Pi | oh-my-pi |
|---|---|---|
| CLI | `pi` | `omp` |
| Published CLI package | `@earendil-works/pi-coding-agent` | `@oh-my-pi/pi-coding-agent` |
| Default user directory | `~/.pi/agent/` | `~/.omp/agent/` |
| Current settings | `settings.json` | `config.yml`; existing `config.yaml` supported |
| Custom models | `models.json` | `models.yml` |
| Saved credentials | `auth.json` | Active auth store, normally SQLite `agent.db` |
| Project settings | `.pi/settings.json` | Working-directory `.omp/config.yml`, plus legacy inputs |
| Execution orchestration | Minimal core, extensible through packages | Built-in `task`, advisor, Agent Hub, and other workflow surfaces |
| Code execution | Optional QuickJS `codemode`, with no direct filesystem/network/Node APIs | Persistent Python/JS `eval`, tool re-entry, and broader host capabilities |
| Shell | Separate non-interactive process per command | Native embedded shell with persistent sessions and in-process utilities |
| Project inputs | Upstream project-trust flow | OMP intentionally loads project inputs; narrowing flags are not a sandbox |

Do not translate upstream commands by replacing `pi` with `omp`. Check OMP's help and docs for flags, settings, session behavior, package installation, and extension APIs. In particular:

- Do not install upstream subagent, MCP, web-search, approval, or LSP packages just to supply features OMP already ships.
- Do not apply Pi's `defaultTools`, QuickJS limits, `auth.json`, `trust.json`, or JSON configuration snippets to OMP.
- Do not assume OMP discovers `.pi` directories. Its generic discovery roots exclude `.pi`.
- Do not assume Pi extensions work unchanged. OMP remaps some legacy host imports, but API compatibility still needs a version-specific smoke test.

Sources: [OMP README][o-readme], [settings][o-settings], [discovery][o-discovery], [providers][o-providers], [legacy import compatibility][o-compat]; upstream [configuration][p-configuration], [codemode][p-codemode], and [security][p-security].

## 3. What comes packaged

“Bundled” means OMP contains the integration. It does not imply the feature is enabled, its external runtime is installed, an account has access, or the feature runs inside a security boundary.

| Bundled surface | Activation or prerequisite | Setup recommendation |
|---|---|---|
| `read`, `write`, hashline `edit`, `grep`, `glob`, structural `ast_grep`/`ast_edit` | Active tool selection and approvals; AST changes have a preview/apply flow | Keep native implementations; do not override their edit format |
| Native shell, PTY, background jobs | Platform support and optional external programs invoked by commands | Use explicit commands; test working-directory and environment persistence |
| Persistent Python/JS `eval` and tool callbacks | `eval.py`/`eval.js` default true; Python requires 3.8+ or `python.interpreter`; JS uses bundled runtime | Configure the intended backends; require approval for execution |
| LSP operations and write-time integration | Enabled by default, lazy server startup; needs root marker and installed server | Configure languages in the current repository; approve dependencies first |
| DAP debugging | `debug.enabled` defaults true; needs a DAP adapter and target tooling | Configure only adapters needed for actual projects |
| Parallel `task` workers and typed yields | Batch tasks default on; typed yields need `task.structured: true` or an agent-specific opt-in; isolation defaults off | Use built-in workers and Agent Hub rather than a subagent package |
| Agent Hub | `Alt+A`; `/hotkeys` shows actual bindings | Use for live progress, transcripts, steering, revive, and termination |
| Agent-definition hub | `/agents` | Inspect imported definitions, models, and tools before enabling them |
| Advisor | Ships disabled; model assignment alone does not enable it | Keep available; start with deliberate review runs rather than reviewing every turn |
| Planning, plan annotations, `/review`, `/annotate` | Planning is enabled but not active on startup; `/review` delegates via the main agent and `task` | Use native workflow first; inspect resulting diffs before publishing |
| Structured `ask` and `todo` | `ask.enabled` defaults true; requires prompt-capable UI; `ask.timeout: 0` prevents timed answer selection | Ask one yes/no question with a recommendation, alternatives, and write-in support |
| `web_search` and URL/PDF/site extraction through `read` | Search credentials or supported keyless backend; network access | Configure existing providers; do not add a web-access extension |
| `pr://`, `issue://`, `skill://`, `agent://`, `history://`, other internal paths | Scheme-specific authentication/context | Reuse them instead of inventing one tool per GitHub operation |
| Browser automation and existing-tab relay | `browser.enabled` defaults true; managed Chromium downloads on first use; relay defaults off | Approve the download; prefer a fresh profile; attach personal tabs only with consent |
| Computer use | Disabled-by-default Eval API, OS permissions, graphical session | Defer host-desktop control until the user asks for it |
| Memory and managed skills | `memory.backend` defaults `off`; current choices include local, Hindsight, Mnemopi, Sharpshooter | Decide retention/backend before enabling capture; control autolearn separately |
| GitHub tool and Codex Security scan integration | Setting-gated, off by default; their own accounts/services | Enable only for a demonstrated workflow; scanning is not a local-only promise |
| Images, TTS, speech/dictation, local tiny models | Model roles, service credentials or downloaded runtimes/weights | Keep optional; do not download models as a side effect of onboarding |
| `checkpoint`/`rewind` | Setting-gated, off by default | Evaluate against normal sessions/compaction before enabling |
| Collaboration and encrypted session sharing | Explicit `/collab` or `/share`; external relay/storage | Leave unused for initial acceptance; require a data-sharing decision |
| Interactive, print, RPC/RPC-UI, ACP, TypeScript SDK | Different entry points and host obligations | Start in the terminal; document automation without deploying a service |
| Existing-agent configuration and plugin discovery | Source-specific discovery policy | Import deliberately; distinguish passive instructions from executable hooks/MCP |

The README's headline tool/provider counts are descriptive, not acceptance criteria. Source settings expose more detail than the README: task concurrency defaults to 32, recursion depth to 2, subagent LSP to off, and automatic application of isolated changes to on. The proposed baseline changes those choices rather than assuming “isolated” means “nothing applies without review.”

Agent Hub and `/agents` are different surfaces: the former controls live workers; the latter manages agent definitions. Killing a persisted worker does not delete its transcript and need not prevent later revival. Sources: [README][o-readme], [Agent Hub][o-hub], [approvals][o-approvals], [skills][o-skills], [slash-command behavior][o-commands].

## 4. Installation and version ownership

### Supported platforms

OMP documents macOS and Linux on arm64/x64, with baseline and AVX2 x64 variants. Confirm the machine architecture and release artifact before installing. The source reviewed does not establish a minimum macOS version or glibc version; do not invent one. Alpine/musl release binaries need `libstdc++` and `libgcc`.

### Choose exactly one owner

| Method | Recommendation | Upgrade/rollback consequence |
|---|---|---|
| Bun package | Preferred when using Bun for OMP development/extensions; upstream labels this recommended | Require Bun `>=1.4.4`; pin the OMP package version and use the same manager to change it |
| Standalone release binary | Good cross-platform alternative when avoiding a global Bun runtime | Pin a release tag, retain provenance/checksum, and reinstall the previous tested tag to roll back |
| Homebrew | Acceptable when Homebrew should own macOS software | Use `brew install can1357/tap/omp`; record the installed version; do not promise arbitrary historical formula rollback |
| Nix/Home Manager | Best fit for an existing Nix-managed host | Pin the flake revision and keep configuration under that manager |
| Source checkout | For developing OMP itself | Requires workspace setup and the Rust/N-API build; not the default onboarding route |

Do not install upstream Pi as a prerequisite. Do not install OMP through multiple managers or alias `pi` to `omp`.

Proposed Bun installation after approval, using the researched version as a candidate:

```bash
bun --version
bun install -g @oh-my-pi/pi-coding-agent@18.16.0
command -v omp
omp --version
omp --help
```

Confirm that the chosen release's help/schema matches this document. The indexed source commit is not a claim that every mutable download URL or current release points to that commit.

For the standalone route, download the installer to a temporary file, inspect it, and invoke it with `--binary --ref v18.16.0` after approving the selected release. `--ref` alone selects source mode. OMP's installer checks the downloaded binary's SHA-256; a checksum from the same distribution channel is an integrity check, not an independent publisher signature.

Record the installation owner, executable path, OMP version, runtime version, OS/architecture, and selected release reference. Do not run `bun setup` in the source checkout unless developing OMP. Source: [README installation][o-readme], [installer][o-installer], [CLI package][o-package].

## 5. Configuration, profiles, and secrets

### Native layout

Recommend a named `personal` profile for this onboarding. It separates native OMP state from a future `work` profile; it does not isolate processes or external configuration sources.

```text
~/.omp/profiles/personal/agent/
  config.yml             # portable non-secret settings
  models.yml             # only if a custom endpoint or verified override is needed
  AGENTS.md              # short OMP-specific user preferences
  keybindings.yml        # only intentional profile overrides
  .env                   # optional private search credentials, never committed
  agent.db               # sensitive runtime/auth state at the normal location
  sessions/              # sensitive conversation history and artifacts

<repository>/.omp/config.yml  # optional, non-secret, cwd-scoped project settings
```

Paths above assume no XDG relocation. Use `omp --profile personal config path` to establish the active agent directory. Existing XDG data/state/cache category directories can relocate `agent.db`, sessions, and other state without moving `config.yml`. Inventory actual resolved paths before backup or cleanup. Named profiles ignore `PI_CODING_AGENT_DIR`; they inherit default-profile keybindings underneath their own overrides. Foreign agent roots are not profile-scoped.

### Make profile selection persistent

The policy and credentials in `personal` do not apply to the default profile. A one-time `export` in a login example is insufficient: a later plain `omp` in a fresh shell otherwise returns to the default profile, whose approval default is `yolo`.

After approving shell changes, add the following to one managed OMP block sourced by the user's actual zsh/bash startup file, alongside the completion setup:

```bash
export OMP_PROFILE=personal
```

For fish, use its shell-specific equivalent, `set -gx OMP_PROFILE personal`, in the managed fish startup block. Do not source bash syntax into fish. Inventory launch paths such as SSH shells, tmux/cmux panes, IDE terminals, and automation: they must inherit this variable or pass `--profile personal`. An explicit `--profile` can override the environment.

Open a fresh terminal and verify, without relying on the previous shell:

```bash
omp config path
omp config list --json
```

The path must select `personal`, and the effective values must match the candidate below, including `tools.approvalMode: always-ask`. Stop on a mismatch. All unqualified `omp` examples after this point assume this verified startup configuration. Until it exists, prefix each invocation with `OMP_PROFILE=personal` or use the documented `--profile personal` form; do not troubleshoot missing logins by authenticating the default profile.

For interactive sessions, use the explicit launch:

```bash
omp --profile personal --approval-mode always-ask
```

A reviewed shell shortcut may wrap that invocation, but it does not replace the persistent profile selection for subcommands. The runtime flag pins the approval mode above project settings; it does not pin per-tool rules or suppress startup inputs. Neither `--yolo` nor `--auto-approve` belongs in the shortcut. Automation outside an interactive shell must select the profile explicitly and must not run this interactive policy without a defined headless tool policy.

### Precedence and edit ownership

Settings resolve from low to high:

```text
defaults < global/profile YAML < project settings < config overlays < runtime overrides < declared setting environment variables
```

`PI_CONFIG_FILES` overlays load before explicit repeated `--config` files; later overlays win. Some declared environment variables act as fallbacks instead of overrides. API credential resolution follows a separate chain.

Mappings deep-merge. Arrays replace rather than append. A project `disabledProviders` array can therefore remove the global restrictions unless it repeats them. Native project settings are cwd-scoped, not nearest-ancestor settings. Discovered foreign settings have additional source-order behavior; do not rely on a global file as a mandatory policy boundary.

Project configuration can also change `tools.approvalMode` or replace a `tools.approval` entry with `allow`. The launch flag above protects the mode only: an explicit tool policy can still allow a call in `always-ask`. Inspect project inputs before startup and compare all effective per-tool policies in the target directory. Reject an unreviewed override rather than treating a named profile or shortcut as tamper-proof policy enforcement.

`omp config set` writes the active global/profile file. It is not a general project-settings editor. Project model-role assignments have a separate `modelRoleStorage: project` option; other project keys require editing the project file.

Use nested YAML, not dotted literal keys. The assembled candidate in section 8 is the configuration template; the smaller search example explains routing and is not another file to overlay or paste over it.

Unknown or invalid ordinary settings can warn and revert to defaults. A syntactically valid YAML file is not proof that the configuration works. Verify effective values with `omp config list --json` and individual non-secret `config get` calls. `config list` masks declared credential fields; `config get` can print secrets, so never use it to inspect credential values.

### Credential handling

Use OMP's own login flows rather than copying Claude Code, Gemini CLI, or Codex token files. Keep search keys in the launch environment supplied by an existing secret manager, or in the active profile's private `.env` if the user approves that fallback. Never put keys in `config.yml`, `models.yml`, a shell command argument, a committed project `.env`, or this spec.

OMP's dotenv loader checks non-empty process values, project `.env`, profile agent `.env`, profile-root `.env`, and `~/.env` in that order. Bun may preload dotenv variants first. A named profile does not neutralize a project `.env`. Run from a reviewed working directory and check only whether expected variables are set, never their values.

Protect private directories/files with owner-only permissions and OS disk encryption. Treat `agent.db`, SQLite sidecars, sessions, exports, caches, and backups as sensitive; do not assume macOS Keychain or Linux Secret Service encrypts the auth database. Use a consistent snapshot or SQLite backup mechanism when backing up a live database, not an uncoordinated copy of one SQLite file.

Enable `secrets.enabled: true` as defense in depth. Its obfuscation does not redact static system prompts/tool definitions, all binary content, or arbitrary unknown payloads; it is not at-rest encryption or a reason to print secrets.

Sources: [settings][o-settings], [discovery][o-discovery], [credential and dotenv precedence][o-providers], [secret obfuscation][o-secrets].

## 6. OAuth and model selection

### Provider identity matters

| Requested access | OMP provider | Flow and caveat |
|---|---|---|
| Gemini OAuth | `google-gemini-cli` | OMP implements Gemini CLI/Code Assist login; Google's current documentation prohibits direct third-party access through this route |
| Alternate Google OAuth | `google-antigravity` | Separate backend; Google's Additional Terms restrict third-party access |
| Anthropic OAuth | `anthropic` | OMP implements subscription login; Anthropic reserves subscription OAuth for its native applications and prohibits third-party Claude.ai login |
| Codex OAuth | `openai-codex` | ChatGPT/Codex subscription route; provider documentation describes official Codex clients, not blanket permission for third-party clients |

The Google API provider `google` uses `GEMINI_API_KEY`; it is not the Gemini OAuth route. The OpenAI API provider `openai` uses `OPENAI_API_KEY`; it is not the Codex subscription route. Discovery IDs such as `gemini`, `claude`, and `codex` identify configuration importers, not those inference providers.

OMP's technical CLI supports `omp login <provider>`. For the proposed baseline, the only candidate subscription login is Codex, and it still requires confirming applicable account/workspace authorization:

```bash
export OMP_PROFILE=personal
omp login openai-codex
```

Do not run the Google or Anthropic subscription login flows under the currently documented restrictions. Browser callback completion and supported pasted callback/device flows depend on the provider. On Linux over SSH, use the flow OMP actually offers; do not expose callback ports on `0.0.0.0`, invent a `--device-code` flag, or copy a refresh token between machines.

Stored OAuth normally outranks provider environment keys; a custom provider's pinned `models.yml` key ranks above stored OAuth. Avoid routing a subscription credential through a custom proxy. Availability in a model picker only proves configured authentication, not a successful request or entitlement.

### Provider-policy findings

| Provider | First-party evidence read on the research date | Setup consequence |
|---|---|---|
| Anthropic | [Authentication and credential use][policy-anthropic] reserves subscription OAuth for native Anthropic apps and prohibits third-party developers offering Claude.ai login or storing/intermediating those credentials | Keep OMP subscription OAuth unused. An authorized Console API key or supported cloud-provider route is a separate, explicitly approved billing decision |
| Gemini CLI / Code Assist | Google's [CLI terms/privacy reference][policy-google-cli] states direct third-party access to its backing services violates applicable terms/policies | Keep `google-gemini-cli` unused. Consider an authorized Gemini API/Vertex route only if the user approves adding that access |
| Antigravity | [Additional Terms, clause 6][policy-antigravity] restrict third-party software accessing the service; the opening paragraph distinguishes some managed agreements | Do not substitute Antigravity for Gemini CLI OAuth. Only documented provider authorization under an applicable agreement could change the decision |
| Codex | [OpenAI's authentication guide][policy-codex] separates ChatGPT subscription and API access for official Codex surfaces | Confirm applicable third-party use and workspace policy before enabling OMP; the guide alone does not certify OMP usage |

These are operational constraints drawn from provider documentation, not a claim about whether an account has faced enforcement. User approval by itself cannot override provider restrictions. If an applicable provider agreement grants an exception, record that authorization without committing private agreement details. Otherwise preserve the native first-party tools for subscription use. The user's currently stated access may not support all three model families inside OMP without an access-method change.

### Codex authorization decision

This gate is a documented account-policy decision, not a successful-login test. Before the first OMP Codex login, record the proposed client/access method, account eligibility, applicable terms/guidance with their review date, and one of these outcomes:

- **Affirmative authorization:** applicable provider documentation, an agreement, or provider support covers the intended use; a managed workspace also needs its administrator's approval.
- **Bounded trial with disclosed uncertainty:** after reviewing the applicable terms, the account owner identifies no contrary restriction and records an informed decision to try this third-party client. Record that OpenAI's official-client auth guide does not certify OMP. A managed workspace still requires administrator approval; accepting uncertainty does not override a prohibition.
- **Not approved or unresolved:** do not authenticate. Keep using the first-party Codex client, or ask whether to add separately billed OpenAI API access through provider `openai` and `OPENAI_API_KEY`. The user has not said they have that key, so do not assume it exists or switch billing silently.

A bare “the token works,” eligibility for the official Codex CLI, or an undocumented assumption does not satisfy the gate. If applicable terms contradict the proposed use, user risk acceptance is not an alternative to provider authorization. Record the decision privately without copying account identifiers, tokens, or agreement details into this repository.

Do not patch client fingerprints, impersonate an approved client, reuse tokens from first-party applications, or evade provider restrictions.

### Community OAuth instructions versus a CLI bridge

The user supplied a Reddit setup thread during this research. Reddit returned a JavaScript challenge, a login redirect, and a 403 for its JSON endpoint; the post's actual instructions could not be verified. Do not attribute a package or method to that thread from its title or search results.

OMP already implements an `anthropic` OAuth login path. That technical support does not change the provider-policy findings above. A credential-copying extension such as [`pi-claude-auth`][public-claude-auth] reads Claude Code credentials, seeds Pi's auth store, and refreshes/writes tokens back; its own README calls this a community workaround. Do not add it to this setup.

An official-CLI bridge is a different design. [`@saccolabs/pi-claude-cli`][public-claude-cli] documents using an authenticated, unmodified `claude` executable while Pi supplies context and tools, without extracting subscription credentials. Its documented test matrix covers upstream Pi, not this pinned OMP release. Investigate provider authorization, OMP API compatibility, inherited Claude hooks/settings, tool-approval enforcement, history/compaction fidelity, and subprocess cleanup before considering that route. It is not a selected plugin, a verified OMP built-in, or an approved exception to provider policy.

Sources: [providers][o-providers], [OAuth transport details][o-quirks], and the first-party policy references above.

### Role plan

Configure OMP's `modelRoles` in `config.yml`. Do not populate `models.yml` with copies of built-in models. Choose exact selectors from the installed OMP catalog and confirm each through a small live request after approval.

| Role | Proposed use | Selection rule |
|---|---|---|
| `default` | Everyday coding | Start with an authorized Codex coding model; user may choose Anthropic if permitted |
| `task` | General delegated implementation | Same verified coding family; explicit agent overrides only when needed |
| `smol` | Bounded lookup and lightweight workers | Lowest-cost/lowest-quota suitable model from an authorized account |
| `slow` / `plan` | Architecture and difficult reasoning | Strong reasoning model; enable high effort for the task rather than every lookup |
| `advisor` | Independent second opinion | Off in the Codex-only baseline; add cross-family review only after authorizing another access method |
| `vision` | Screenshots and images | A verified image-input model from the configured accounts |
| `commit` | Commit-message drafting | Reuse a configured model; retain human control over Git operations |
| `tiny` / `memory` / `widget` | Background helpers | Reuse the verified model for title/widget helpers initially, with quota use disclosed; memory stays off |
| `web` | Search | Native search/grounded model role, configured separately below |
| `judge` | Internal classification/judgment helpers | Pin to `@default` in the baseline so an unassigned role does not try another service |
| `image` / `speech` / `dictation` | Optional generation and non-chat workloads | Configure only when adopting those features |

List OMP's catalog, not Copilot's model names:

```bash
omp models --kind chat
omp models --kind search
omp models --kind all
```

Open `/model` and its Roles view to assign the verified selectors. A comma-separated role value selects the first available candidate; it is not a failure retry policy. `retry.fallbackChains` handles failover. An explicit empty role chain disables its fallbacks; model-kind roles have their own defaults and do not inherit chat's `default` chain.

Recommend explicit chat roles and **no automatic cross-provider chat failover during onboarding**. Record any later failover decision because it changes where repository context goes and which subscription/API quota it consumes. Keep normal retries bounded; do not treat authentication failures as permission to switch billing paths.

The requested Gemini 4 Argon and Opus 5.5 reviewers for this document are review choices in the current assistant environment. They do not prove that `gemini-4-argon` or `claude-opus-5.5` are valid OMP provider model IDs or are included in these subscriptions.

Source-backed OMP examples include `openai-codex/gpt-6.1-sol`, `anthropic/claude-sonnet-5-5`, and `anthropic/claude-opus-5-5`. Source tests include `google-antigravity/gemini-4-argon`; that does not prove a `google-gemini-cli/gemini-4-argon` route or account entitlement. Do not use any of these selectors until its access method passes the policy gate and its installed catalog lists it.

Sources: [settings and roles][o-settings], [model configuration][o-models], [upstream catalog][p-model-catalog].

## 7. Built-in search and extraction

OMP already supports every search access method in the user's inventory. No Tavily, Firecrawl, Brave, or provider-search MCP is required for baseline functionality.

### Routing proposal

Prefer an explicit chain over the default broad automatic chain so the user knows which services receive queries. Proposed initial order:

1. Tavily using the existing key.
2. Brave using the existing key.
3. Firecrawl using its key when configured, or its supported keyless search path when no key exists.

OMP also implements OAuth-grounded Gemini/Anthropic/Codex search. Keep prohibited subscription routes unused; consider an authorized grounded route as a deliberate alternative, not a free fallback.

Source-supported configuration for the keyed-provider chain:

```yaml
modelRoles:
  web: web/tavily
retry:
  fallbackChains:
    web:
      - web/brave
      - web/firecrawl
```

Before applying this template, confirm the selectors in `omp models --kind search` for the installed release. Do not use the retired `providers.webSearch`, `webSearchOrder`, or `webSearchExclude` keys.

For a one-off provider probe:

```bash
omp web-search --model web/tavily "oh-my-pi configuration documentation"
omp web-search --model web/brave "oh-my-pi configuration documentation"
omp web-search --model web/firecrawl "oh-my-pi configuration documentation"
```

The in-session `web_search` tool follows the configured `web` role and fallback chain; it does not expose a per-call model override. The CLI's `--model` is a separate interface.

The README's backend labels `gemini`, `anthropic`, and `codex` are not `web/gemini`, `web/anthropic`, or `web/codex` model selectors. Grounded search uses a real grounding-capable provider/model, for example documented `openai-codex/gpt-6-luna`, or an available Google OAuth model when authorized.

The current default priority list is `web/parallel` → `web/hosted` → `web/exa` → `web/firecrawl` → `web/searxng` → `web/startpage` → `web/duckduckgo` → `web/ecosia` → `web/google` → `web/mojeek` → `web/public`. `web/hosted` expands through the active provider's supported grounded models; Public Web is explicit-only despite appearing in the list. Merely exporting Tavily/Brave keys does not add them to that default chain. An explicit `web` fallback list replaces default fallback entries; `[]` keeps only the primary.

Provider attempts run sequentially. `providers.webSearchTimeoutSeconds` defaults to 60 seconds per transport, not for the whole chain. Grounded answer-only results without sources/citations fail validation. Inspect search results for reported errors: the tool can return an `Error:` text plus `details.error` rather than throwing.

### Firecrawl's keyless boundary

Firecrawl search can issue an unauthenticated request when no credential resolves. Its URL-scraping helper requires a credential. Do not promise keyless extraction, unlimited requests, or automatic retry-without-key after an invalid-key response. Endpoint availability and rate limits remain external service behavior.

Use native `read` for ordinary URLs, PDFs, package registries, GitHub pages, and supported site-specific extraction. Add a dedicated external crawl integration only for a missing requirement such as a persistent crawl job, not for URL fetching OMP already handles.

### Data and quota controls

Search sends queries to outside services. Do not include private code, internal URLs, customer data, or secrets in a public search. Search failover also changes recipients. With all three keys supplied, exercise each route independently and record its selected backend, citations, latency, and error behavior without logging credentials. Test keyless Firecrawl only in a controlled environment with both environment and stored search credentials absent.

Sources: [README search table][o-readme], [role routing][o-settings], [web-search contract][o-search-doc], [search dispatch][o-search], [Firecrawl search][o-firecrawl-search], [Firecrawl scraping][o-firecrawl-read].

## 8. Coding workflow, approvals, and external dependencies

### Interactive approval policy

OMP's schema default is `yolo`. Recommend `always-ask` plus explicit per-tool prompt policies in the assembled candidate below.

`always-ask` automatically permits read-tier operations and asks for writes/execution. `write` is a later ergonomic option: it permits writes but still asks for execution. `always-ask-cached` can additionally gate file reads. None creates an OS sandbox.

**Interaction cost:** explicit `prompt` rules for `bash` and `eval` ask on every call and do not offer session-wide approval. Even `git status`, `ls`, or a test run needs a prompt when routed through Bash. Prefer native read/search tools for inspection. Keep this conservative baseline initially rather than switching to `yolo` to silence prompts.

If that cost proves excessive, the user can approve an optional exact-command allowlist for a reviewed repository:

```yaml
bash:
  allowCompoundCommands: false
  patterns:
    - match: "git -c core.fsmonitor=false status --short"
      approval: allow
    - match: "git --no-pager diff --no-ext-diff --no-textconv"
      approval: allow
    - match: "git --no-pager log --no-ext-diff --no-textconv --oneline -5"
      approval: allow
```

This is an optional amendment, not part of the assembled baseline. Exact tool-declared allows outrank the per-tool `bash: prompt` rule, so these spellings can also run in headless workers. Do not add wildcards, compound commands, test runners, package managers, or arbitrary scripts. The explicit Git options avoid the usual pager, fsmonitor, external-diff, and textconv execution paths for these commands; trusted executables/configuration and OS isolation still matter. A different spelling continues to prompt.

Per-tool rules, critical-command policies, Eval execution, browser control, MCP calls, and foreground desktop acquisition have separate behavior. Do not approve `bash` broadly and assume `eval` cannot execute the same command. Restricted folders do not parse paths embedded in shell text and do not provide filesystem containment.

Opening a project can load executable inputs before a model tool approval appears. Review project `.omp`, foreign-agent configuration, hooks, tool modules, plugins, and MCP definitions before launching. Use an external container/VM or dedicated account for untrusted repositories. A profile, workspace clone, Git worktree, restricted-folder list, or read-only prompt is not a substitute.

For narrowing an invocation, OMP documents `--no-extensions` and exact `--trusted-extension` paths. A nested YAML overlay containing `mcp.enableProjectConfig: false` excludes project-level MCP sources, including foreign project formats, but not user-level MCP sources. `--no-tools` does not suppress separately discovered project tool modules. Do not advertise these switches as a complete “safe mode.”

### Subagents and advisors

Use built-in `task` for independent work; enable `task.structured` for typed yields. The candidate limits concurrency to two, allows isolation, and disables automatic application of isolated changes.

`task.isolation.enabled` permits per-item `isolated: true`; it does not force every worker into isolation. Require that flag for concurrent writers and inspect the resulting patch/branch before integration. Isolation is unavailable for plan-mode workers.

Require isolation for **every** writer task, including a single writer. Before approving, inspect the actual task input and verify `isolated: true` for each writing item, its agent, scope, and destination. The pinned [task approval formatter][o-task-approval] summarizes assignments but does not print `isolated`, and a batch summary can omit later assignments. A prose promise of isolation, or an isolated-workspace setting, is not evidence that the submitted flag is present.

Use the host's raw tool-input inspection if it exposes the complete pending call. If the host cannot expose the isolation flag and every writer assignment before execution, deny host-side writer delegation and use read-only workers or a separately approved externally isolated workflow. This spec does not claim configuration alone enforces isolation. `apply: false` only delays applying changes from tasks that actually ran isolated; a non-isolated child can edit the shared checkout directly.

**Important: OMP intentionally runs headless task children in `yolo` mode. Approving the parent's `task` call authorizes their ordinary tool execution; they do not inherit the parent's `always-ask` interaction.** User denies remain absolute, and a policy that still requires a prompt rejects because a headless worker cannot answer it.

Begin with the bundled `scout` agent for bounded read-only research. Do not assume the bundled `reviewer`, `task`, or `sonic` agents are read-only. Agent frontmatter tool lists restrict built-ins, but MCP/extension/custom tools can remain additive. Inspect the complete effective surface, limit scope, and use external isolation for untrusted work. Explicitly approve this child-authorization model before enabling writer delegation.

Set `tools.approval.task: prompt` so each task invocation asks, without an “approve task for this session” shortcut. One approved batch can still authorize multiple workers. The candidate also sets `bash`, `eval`, and `browser` to explicit `prompt`: a headless child cannot satisfy those policies and its corresponding calls fail rather than execute. This permits bounded read/file-edit delegation, not unattended shell/test/browser workers. The main agent runs commands/tests through separate interactive approval; relaxing that restriction requires another policy decision.

User denies remain useful for additional restrictions, but a short list of shell spelling patterns cannot provide containment. The broad prompt policies avoid pretending that a handful of `rm`/Git patterns covers alternate flags, executable paths, Python subprocesses, or imported tools. Extension/MCP surfaces still need inspection.

Use `Alt+A` to inspect live workers; `/agents` to manage definitions. Keep advisor disabled in the Codex-only baseline. After adding an authorized second model family, decide its model, context disclosure, quota, latency, and cadence before enabling it.

### Assembled candidate `config.yml`

This is the single proposed profile template. **Do not apply it with the unresolved selector placeholder.** Replace it with one exact OMP catalog selector only after the provider gate and live capability probe pass. `openai-codex/gpt-6.1-sol` is a source-backed example, not a guarantee of account access. If no approved model is available, stop before launching a model-backed session.

All other chat roles below reuse that selector or its aliases for the Codex-only baseline; this makes no claim of cheaper `smol` work or cross-family independence. Confirm image-input support before accepting the `vision` assignment.

```yaml
modelRoles:
  default: "<verified-codex-coding-selector>"
  task: "@default"
  smol: "@default"
  slow: "@default"
  plan: "@slow"
  vision: "@default"
  commit: "@default"
  tiny: "@default"
  widget: "@default"
  advisor: "@slow"
  judge: "@default"
  web: web/tavily
defaultThinkingLevel: medium
enabledProviders: []
disabledProviders:
  - anthropic
  - google-gemini-cli
  - google-antigravity
skills:
  enableClaudeUser: false
  enableClaudeProject: false
  enableCodexUser: false
  enableAgentsUser: false
  enableAgentsProject: false
tools:
  approvalMode: always-ask
  approval:
    task: prompt
    bash: prompt
    eval: prompt
    browser: prompt
secrets:
  enabled: true
ask:
  enabled: true
  timeout: 0
task:
  maxConcurrency: 2
  maxRecursionDepth: 1
  structured: true
  enableLsp: false
  isolation:
    enabled: true
    apply: false
    merge: patch
isolation:
  backend: auto
advisor:
  enabled: false
memory:
  backend: "off"
autolearn:
  enabled: false
eval:
  autoProvision: false
browser:
  enabled: false
computer:
  enabled: false
mcp:
  enableProjectConfig: false
retry:
  modelFallback: false
  fallbackChains:
    default: []
    web:
      - web/brave
      - web/firecrawl
```

`disabledProviders` blocks the restricted subscription routes; it also blocks Anthropic API access until that provider entry is removed as part of approving a different access method. Empty `enabledProviders` keeps foreign user discovery opt-in. The skill-source switches additionally exclude broad Claude, Codex-user, and `.agents` skill imports; they do not disable every foreign configuration capability. Native skills, native plugin registries, project inputs, and other source providers still need inspection. Project MCP and the browser start off in this candidate, so enabling either after review is an explicit configuration change. Read-only research can still use native URL reading/search.

`modelFallback` governs chat failover; search follows its own configured chain. Review any existing per-model fallback entries too. Adopt a [memory backend][o-memory-settings] and automatic learning only after deciding retention, model use, and source scope. A question timeout must not select a recommended answer in place of a user decision.

`eval.autoProvision` defaults to true upstream; the candidate sets it false. This prevents the first `%bun add` from creating a missing managed JavaScript package environment without first changing that policy or explicitly selecting another environment. It does not disable Python/JS execution, prevent installs into an existing environment, or make package managers harmless. Every dependency installation still needs explicit approval; do not select `%environment project` just to bypass the gate and mutate a repository's package files.

### Language/runtime prerequisites

Configure the bundled integration without assuming it bundles every external executable:

| Capability | macOS | Linux | Acceptance gate |
|---|---|---|---|
| LSP | Existing repository toolchain, cwd root marker, installed language server | Same, installed through the repository's normal manager | Lazy diagnostics and navigation work; no unapproved global installs; parent-root detection is not assumed |
| DAP | Chosen LLDB/Go/Python adapter and target tooling | Same, subject to debugger/ptrace/container restrictions | One disposable debug session attaches or reports the missing prerequisite |
| Python/JS Eval | Required backend/runtime with approved dependencies | Same; headless support depends on operation | Cells persist state; execution still follows intended approvals |
| Browser | Managed Chromium downloads on first use, or a selected CDP/relay target | Browser libraries and graphical/headless environment as selected | Approve the download; use a disposable profile/public page; no personal-cookie import |
| Computer use | Grant Screen Recording/Accessibility to the launching terminal/IDE and restart; capture backend varies by OS version | X11 needs display/RandR/XTEST and AT-SPI for accessibility; released binaries omit PipeWire capture on Wayland | Leave disabled; inspect `computer.capabilities()` before promising capture/input |
| Local models | Optional Apple Silicon/CPU/GPU stack | Optional compatible inference server or CPU/GPU stack | No downloads until resource budget, license, and intended use are approved |

Preserve the user's current terminal and tools. Do not install all language servers, debug adapters, desktop helpers, voice backends, or local weights to make an inventory look complete.

Sources: [approvals][o-approvals], [README project inputs][o-readme], [Agent Hub][o-hub], [task settings][o-task-settings], [agent discovery][o-agents], [LSP][o-lsp], [browser][o-browser], [Eval][o-eval], [computer use][o-computer], [local runtimes][o-local].

## 9. Existing instructions, skills, MCP, and packages

### Reuse without importing everything

OMP discovers native configuration and several foreign formats. Foreign user-level sources are opt-in through `enabledProviders`; foreign project sources can load by default. `enabledProviders` is **not an inference-provider allowlist**. `disabledProviders` shares an ID namespace across inference providers and discovery sources, so confusing `claude` with `anthropic` or `gemini` with `google` has different effects.

Start with native OMP preferences and the reviewed project's existing instructions. Adopt the selected public plugins and standalone skills only in the final stages in section 15. Do not point OMP at this checkout's whole `.claude/skills`, or the user's whole Claude/Copilot/shared skill roots: those roots mix requested, unrequested, and organization-specific components.

For the final standalone stage, use an approved-only root whose immediate children contain `SKILL.md`; nested category trees are not scanned recursively:

```yaml
skills:
  customDirectories:
    - ~/.omp/profiles/personal/agent/approved-skills
```

Populate that root only from the public sources and approved winners in section 15. Preserve skill-relative scripts/references, attribution, and provenance. Symlink/identical-content dedup and precedence can change visible names; confirm the resolved source and final name of each skill. A familiar name is not proof that its body came from the approved public upstream.

Both `AGENTS.md` and `CLAUDE.md` have discovery support, but do not assume same-directory files concatenate. OMP keeps one project context file per directory depth according to provider priority. Avoid adding another copy of this repository's generated policy.

Use the discovered `/skill:<name>` command, or the resolved namespaced form shown by OMP. Do not assume a Claude plugin's `/plugin:skill` invocation names an OMP skill. Reading a skill's instructions does not provide Claude-only hooks, Copilot tools, or an executable the skill expects.

### MCP and source inventory

OMP has built-in MCP support and imports configuration from other ecosystems. Inventory server names, scope, transport, executable/endpoint, tool names, and auth method without printing keys. Do not import the existing user MCP configuration wholesale. Evaluate only the selected public plugins' MCP definitions in section 15; no organization-specific servers belong to this adoption plan.

Use `/mcp list`, `/mcp test <name>`, `/mcp resources`, `/mcp prompts`, and `/mcp reload` as appropriate. `mcp.enableProjectConfig: false` excludes all project-level MCP sources before deduplication; it does not disable user-level sources. Use `disabledServers` for unwanted server names. Built-in browser availability can filter recognized browser MCP servers from the visible list, so compare discovered inputs with the effective inventory rather than assuming every missing entry failed to load.

Check whether inherited hooks, commands, MCP servers, agents, and plugin entry points actually match OMP's contracts. A Claude plugin manifest or hook command is not proof of lifecycle compatibility. Do not enable all foreign user roots merely to obtain a few skills.

### Package catalog decisions

The supplied [Pi Package Catalog][p-packages] is useful for discovering extensions, skills, templates, and themes. It is an upstream catalog, not a certified OMP compatibility registry.

| Catalog capability/examples | OMP overlap | Recommendation |
|---|---|---|
| `pi-web-access`, `pi-web-search` | Built-in web search, URL/PDF/site extraction | Do not install for baseline search |
| `pi-subagents`, `@tintinweb/pi-subagents` | Built-in task workers and Agent Hub | Do not install to add workers |
| `pi-mcp-adapter`, `pi-mcp-extension` | Built-in MCP | Do not install to add MCP |
| `pi-lens` | Built-in LSP/diagnostics integration | Configure native LSP first |
| Questionnaire/todo packages | Built-in `ask`/`todo` | Use native question/task surfaces |
| `pi-advisor-flow` | Built-in advisor | Use native advisor first |
| `pi-memory` | Native memory backends; a QMD-specific workflow might differ | Evaluate only for an identified retrieval gap |
| LangSmith, Langfuse, Braintrust packages | External observability may be useful | Optional follow-up; review payload export, compatibility, and credentials first |
| Themes/footer packages | Existing TUI customization | Optional, after functional acceptance |

Catalog descriptions and download counts are not evidence of code review or compatibility. Before adding a package, record its purpose, repository, exact version/commit, license, dependencies/install scripts, tool/command collisions, data recipients, OMP API compatibility, and removal procedure. Test one package at a time in a separate profile/disposable repository. The user's selected documentation/workflow plugins in section 15 are intentional follow-up scope; they do not replace OMP's native runtime tools.

Sources: [discovery][o-discovery], [settings][o-settings], [context files][o-context], [skills][o-skills], [MCP configuration][o-mcp], [legacy compatibility][o-compat], [package catalog][p-packages].

## 10. Terminal, shell, sessions, and local models

### Terminal and shell

Use a modern terminal with extended-key support. Retain the existing terminal; do not replace it as part of OMP installation. For macOS/cmux, verify input and native fork placement before adding a bridge. OMP already documents `/fork pane`, `/fork window`, and `/fork tab` integration with supported multiplexers including CMUX. Its CMUX launch requires confirmation that the destination shell accepts POSIX syntax.

Upstream Pi's terminal/tmux guidance is a troubleshooting reference, not a list of guaranteed OMP bindings. Run OMP's `/hotkeys` and test:

- newline versus submit, follow-up/steering, interrupt, external editor, image paste;
- Agent Hub, model selection, terminal resize, scrollback and mouse selection;
- the same actions over SSH and inside a multiplexer if used.

For tmux 3.5+, upstream recommends:

```tmux
set -g extended-keys on
set -g extended-keys-format csi-u
```

For tmux 3.2-3.4, use only `extended-keys on`. Test in a separate server or schedule a restart; do not kill the user's running tmux server. Upstream notes a tmux 3.6 startup-input issue, so verify the installed version before attributing problems to OMP.

Older Ghostty `shift+enter=text:\n` mappings can erase the distinction between modified Enter and a raw newline. Inspect conflicting mappings before editing shared Ghostty/cmux settings; do not apply Pi-specific terminal changes blindly.

Generate OMP completions for the current shell using `omp completions zsh`, `omp completions bash`, or `omp completions fish`. Review a generated file and add one managed shell-initialization entry rather than appending duplicates. Do not source `.zshrc` into an agent's Bash session or assume aliases such as `gco`, `gpr`, and `clean` are available. Prefer explicit Git commands in prompts and scripts.

### Session operations

Use OMP's own session contract:

| Need | OMP operation | Important distinction |
|---|---|---|
| Continue recent work | `omp --continue` | Confirm selected working directory and restored model |
| Choose work | `/resume` or `omp --resume` | Selection can change working directory/configuration |
| Start over | `/new` | New session identity |
| Recover provider stream state | `/fresh` | Preserves transcript; requires no active stream |
| Clear live context | `/clear` | Keeps persisted history; does not erase secrets from disk |
| Branch | `/fork`, or a supported placement variant | Forking history is not filesystem rollback |
| Reduce active context | `/compact` | Summarization is not deletion |
| Inspect/export/share | `/context`, `/dump`, `/export`, `/share` | Different payloads and privacy properties |

Use native compaction defaults first. Upstream's `reserveTokens`/`keepRecentTokens` reference and JSONL v3 describe Pi, not a guarantee of OMP's current schema or compaction method. Inspect OMP's settings before tuning. Do not import an upstream session file without an explicit compatibility path and backup.

OMP HTML exports can contain raw prompts, tool definitions/results, images, and child transcripts. `/dump` can leave sensitive temporary sidecars. OMP's default `/share` path encrypts a snapshot, but the complete link carries its decryption key; custom share handlers have their own privacy behavior. Neither local obfuscation nor encryption grants permission to share work data. Keep uploads and collaboration out of onboarding smoke tests.

### Optional local models

Local models are a follow-up, not a prerequisite for the three OAuth accounts. OMP has native Ollama, llama.cpp, and LM Studio discovery plus optional tiny-model and platform-specific integrations.

Use OMP's `LLAMA_CPP_BASE_URL` and `LLAMA_CPP_API_KEY` for its llama.cpp provider. The supplied upstream Pi guide uses `LLAMA_BASE_URL`/`LLAMA_API_KEY`; those names must not be copied into an OMP setup. Bind local services to loopback unless a separate remote-access design authorizes otherwise.

Approve model licenses, disk/RAM/VRAM usage, downloads, and external dependencies before enabling a local backend. Do not assume Apple Silicon GPU acceleration, Linux CUDA availability, or Wayland desktop support. OMP's local-runtime documentation records backend-specific fallbacks and limitations.

Sources: [README completions][o-readme], [OMP sessions][o-sessions], [Agent Hub][o-hub], [providers][o-providers], [local runtimes][o-local]; upstream [terminal][p-terminal], [shell][p-shell], [tmux][p-tmux], [sessions][p-sessions], [compaction][p-compaction], [llama.cpp][p-llama].

## 11. Implementation sequence and acceptance

All commands in this document describe future implementation. Do not mark an acceptance item complete because documentation or a model picker says the capability exists.

1. **Approve decisions.** Confirm install owner, profile, provider authorization, initial models, search order, import scope, and approval mode using section 13.
2. **Inventory without secrets.** Inspect OS/architecture, executable paths, tool versions, terminal/shell startup files and launch paths, reviewed config-source names, and existing installations. Do not read credential values. Record any existing OMP state before migration-capable commands run.
3. **Snapshot and install.** Back up affected settings/state with appropriate permissions. Install the selected pinned release through one manager. Confirm `command -v omp`, version, and help.
4. **Create policy before first project launch.** Configure the approved profile and explicit approvals in a neutral, reviewed directory. Persist profile selection in the approved managed shell block and verify it from a fresh shell before authenticating. Add non-secret settings; do not run setup from an unreviewed repository.
5. **Authenticate permitted providers.** Complete and record the Codex decision above before logging in through OMP. Confirm selected workspace/account, model visibility, one small response, and one tool-using response. Record quota/errors without token values. If the gate does not pass, choose an approved alternative or stop.
6. **Assign roles and search.** Replace the candidate's model placeholder, configure the approved search chain, and compare `omp config list --json` with every intended template value in a fresh shell and the target repository. Check `retry.fallbackChains.web` equals the approved list, not an inherited/default chain; check per-tool prompt policies, disabled routes, both isolation flags, `judge`, and `eval.autoProvision`. Record mismatches and resolve their precedence before continuing.
7. **Adopt bundled workflows.** Exercise read-only task delegation/Agent Hub first. Prove complete pending writer-input inspection in a disposable repository; deny a writer call when `isolated: true` is missing or cannot be verified. Only then exercise an isolated writing task and patch review. Test advisor only if approved. Add LSP for a real project and optional DAP/browser dependencies as required.
8. **Review content without adopting it yet.** Inventory provenance, potential name collisions, MCP definitions, agent toolsets, and plugin/hook compatibility. Do not broaden foreign discovery or install the selected ecosystem before core acceptance.
9. **Exercise terminal and persistence.** Test active keybindings, a normal restart/resume, compaction, working-directory behavior, and optional multiplexer placement without killing existing sessions.
10. **Accept the core and snapshot it.** Complete the core acceptance matrix and retain a consistent baseline snapshot before adding plugins.
11. **Adopt selected public marketplaces/plugins.** Follow section 15's component and provenance gates, then accept the plugin layer independently.
12. **Install selected standalone skills last.** Finish section 15's curated skill stage after the core and plugin layers pass. Record deferred/blocked items and hand over the combined non-secret source manifest and rollback procedure.

### Acceptance matrix

| Area | Evidence required |
|---|---|
| Installation | One installation owner; expected executable/version on both target platforms, or a clear platform-specific blocker |
| Configuration | Fresh-shell plain `omp config path` selects `personal`; `omp config list --json` matches intended settings in neutral and target directories; explicit interactive launch pins the mode; no ignored/invalid-key warnings |
| OAuth | Codex evidence/decision recorded before login; every permitted provider completes a real response/tool round trip; prohibited/unauthorized providers remain unused |
| Models | Exact provider/model selectors and resolved role assignments, including `judge`, recorded; no unintended API-key or cross-provider fallback |
| Search | Independent Tavily/Brave/Firecrawl probes; selected backend and citations visible; controlled fallback failure case |
| Keyless boundary | Search-only behavior confirmed where available; no claim that unauthenticated scraping works |
| Approval | Denied harmless test action does not execute; parent behavior matches approved mode; user understands child `yolo` authorization and inherited denies |
| Workers | Complete raw writer assignments/isolation flags visible before approval, or host writers stay unused; a missing/unverifiable flag leads to denial and no fixture edits; headless shell/Eval probes fail under baseline prompt policies; isolated file changes wait for patch acceptance |
| Discovery | Expected context/skills present once; source provenance known; no unintended MCP/hook launch |
| Public-only adoption | Only approved public sources/components in the OMP registries and effective loadout; no broad import from mixed user roots; excluded and unresolved items remain uninstalled |
| Dependencies | Missing LSP/DAP/Eval/browser prerequisites produce a specific blocker; `eval.autoProvision` is false and missing managed-environment provisioning fails until approved; no silent global installation |
| Sessions | Resume restores expected cwd/model; compaction preserves needed context; no export/share upload |
| Secrets | No values in committed files, recorded output, shell history, screenshots, or handover; private state/backup permissions established |
| Upgrade recovery | Previous installation reference and consistent state snapshot available; schema migration consequences documented |

Do not deliberately rotate tokens, exhaust subscription quotas, break a production workspace, or invoke a consequential command to test the setup.

If demonstrating that non-isolated children write into their parent checkout, use only a disposable Git repository and a harmless fixture file with explicit approval for that negative-control experiment. Do not test that behavior on this working tree or use it to bypass the production writer-approval rule.

## 12. Upgrades, rollback, and removal

Check updates with `omp update --check`. Apply updates through the selected installation owner. Do not mix a Homebrew/Nix/Bun-managed install with an unreviewed self-update path. Treat `omp update --plugins` as a separate dependency change, not routine CLI maintenance.

Before an upgrade, stop writing sessions and take a consistent snapshot of settings, auth state, and artifacts. Record the current version and extension/package versions. Read release notes and compare registered keys, provider flows, and extension APIs. Re-run the acceptance subset affected by the upgrade.

For rollback, reinstall the previous pinned version through the same owner. Restore the matching state snapshot if migrations made the newer state incompatible; do not assume a downgraded binary can read a migrated database or session. Preserve newer data separately rather than overwriting it without review.

For removal, first inventory the actual active/default/named-profile and XDG paths. Remove the executable with its owning manager, remove only the shell entry added for OMP, and decide separately whether to retain sessions and credentials. Removing the package does not imply OAuth revocation. Revoke provider access through its supported account controls when required. Never prescribe blanket deletion of `~/.omp` or another shared root.

Sources: [update implementation][o-update], [settings and migration][o-settings], [discovery paths][o-discovery].

## 13. Approval questions

Ask these one at a time during approval/implementation, not as a prerequisite for drafting. Each accepts **Yes**, **No**, or a **write-in** answer. The user has not selected the recommendations yet.

| Decision | Yes / recommended | No / alternative | Write-in |
|---|---|---|---|
| Use OMP's bundled tools before installing overlapping extensions? | Yes | Evaluate a named extension for a specific gap | Package and reason |
| Use a pinned Bun install on macOS/Linux? | Yes, if Bun `>=1.4.4` is acceptable | Pinned standalone release; Homebrew/Nix when already preferred | Installation owner/version |
| Persist `personal` profile selection in the managed shell block and use an explicit mode-pinned interactive launch? | Yes; verify a fresh shell and each terminal/automation launch path | Use the default profile only after moving the approved policy and credentials there | Profile/launch layout |
| Start with `always-ask` instead of the default `yolo`? | Yes | `write` for trusted coding, after reviewing execution gates | Approval policy |
| Accept Codex-only chat inside OMP and keep Claude/Gemini subscriptions in first-party tools? | Yes, after recording the Codex authorization/trial decision | Approve separately billed OpenAI/Anthropic/Gemini API or a supported cloud-provider route; otherwise keep that work outside OMP | Access method, evidence, and billing limits |
| Use the same verified Codex model across initial chat roles? | Yes; advisor remains off | Choose other available authorized models; cross-family advisor needs another access method | Exact role preferences |
| Use Tavily → Brave → Firecrawl for public search? | Yes | Another explicit order or OAuth-grounded primary | Search policy |
| Keep automatic cross-provider chat failover off initially? | Yes | Approve a named data/usage failover chain | Allowed routes |
| Start with at most two workers and deliberate advisor activation? | Yes | Different concurrency or advisor cadence | Limits/model choice |
| Accept per-call task/Bash/Eval approvals and block headless shell/Eval/browser calls initially? | Yes; expect repeated prompts, including routine shell commands | Approve the exact-command inspection allowlist or a separately designed worker policy; tests still require approval | Agent/tool authorization model |
| Require verified isolation for every writer and leave host writers unused if pending inputs are not inspectable? | Yes | Use a separately approved external isolation workflow | Writer-inspection mechanism |
| Use approved-only sources for the selected public ecosystem, without wholesale user-config import? | Yes; standalone skills come last | Review a narrower public subset; organization-specific content stays excluded | Approved public subset |
| Install one canonical Superpowers and choose one winner for each same-named skill? | Yes; section 15 records the source choices | Select a different public source before installation | Canonical sources |
| Defer desktop control, collaboration uploads, local weights, Eval package-environment provisioning, and telemetry packages? | Yes | Adopt a named capability with approved dependencies and data policy | Feature selection |

## 14. Source coverage

The reading pass covered the full OMP main README and each distinct supplied Pi page, including continuation chunks for long references. The documentation index and package catalog appeared twice in the request; they refer to the same URLs.

Catalog scope: the model catalog's rendered listing and the package catalog landing page, including its 50 displayed package entries. Reading those pages is not an audit of every linked package, all catalog pagination pages, or every model's endpoint. Markdown extraction omitted model names from some table cells; use OMP's own installed catalog for executable selectors.

| Supplied source | Consequence for this spec |
|---|---|
| [oh-my-pi main README][o-readme] | Bundled-capability inventory, installation, search providers, trust model |
| [Pi homepage][p-home] | Minimal upstream philosophy differs from OMP's bundled workflow |
| [Documentation index][p-index] | Navigation and distinction between usage, customization, automation |
| [Quickstart][p-quickstart] | Onboarding concepts; do not copy upstream installer/package |
| [How Pi Works][p-how] | Agent loop, context, sessions, executable extension model |
| [Use Pi in the terminal][p-usage] | Terminal interaction and export risks; verify OMP bindings |
| [Choose a Model][p-models] | Authentication/catalog concepts; distinguish availability from successful inference |
| [Sessions and Context][p-sessions] | Branch/resume/compaction concepts; validate fork-specific behavior |
| [Run Pi safely][p-security] | OS isolation, trust limitations, sensitive sessions |
| [Local Models with llama.cpp][p-llama] | Optional local inference; avoid upstream environment-name leakage |
| [Configure your terminal][p-terminal] | Modified-key and terminal-capability troubleshooting |
| [Configure shell commands][p-shell] | Alias pitfalls; upstream shell behavior differs from OMP |
| [Run Pi in tmux][p-tmux] | Versioned extended-key advice and non-destructive rollout |
| [Configuration][p-configuration] | Upstream JSON/path/schema boundary |
| [Model Catalog][p-model-catalog] | Discovery reference, not account entitlement or an OMP selector contract |
| [Package Catalog][p-packages] | Extension discovery and overlap analysis, not automatic installation |
| [Codemode][p-codemode] | QuickJS boundary differs from OMP Eval; do not copy safety claims |
| [Command Line][p-cli] | Modes/flags must be verified against OMP |
| [Slash commands][p-slash] | Upstream command menu differs from OMP's bundled command registry |
| [Models Configuration][p-model-config] | Custom model metadata concepts; OMP uses its own YAML schema |
| [Environment Variables][p-env] | Separate process, provider, and tool environment; verify fork names |
| [Session File Format][p-format] | Upstream tree/JSONL model; no automatic cross-fork compatibility claim |
| [Compaction Reference][p-compaction] | Context reduction does not delete history; tune OMP independently |
| [SDK][p-sdk] | In-process integration is future work, not terminal setup |
| [CLI Integration][p-cli-integration] | Print/JSON/RPC lifetime and completion semantics need fork verification |
| [Terminal UI][p-tui] | Prefer bundled UI before a custom extension/footer |
| [Virtual Models][p-virtual] | Routing is extensible; native OMP roles meet the initial requirement |
| [Custom Providers][p-custom] | No custom auth/provider implementation needed for supported routes |
| [Extensions][p-extensions] | Executable-code trust, lifecycle/API drift, package review requirements |

### Fork references

Fork links below pin the researched commit. Runtime acceptance still uses the selected installed release.

[o-readme]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/README.md
[o-settings]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/settings.md
[o-discovery]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/config-usage.md
[o-providers]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/providers.md
[o-models]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/models.md
[o-quirks]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/provider-quirks.md
[o-context]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/context-files.md
[o-skills]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/skills.md
[o-compat]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/packages/coding-agent/src/extensibility/plugins/legacy-pi-compat.ts
[o-hub]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/agent-hub.md
[o-commands]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/slash-command-internals.md
[o-approvals]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/approval-mode.md
[o-secrets]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/secrets.md
[o-local]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/local-models.md
[o-sessions]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/session-operations-export-share-fork-resume.md
[o-search]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/packages/coding-agent/src/web/search/index.ts
[o-firecrawl-search]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/packages/coding-agent/src/web/search/providers/firecrawl.ts
[o-firecrawl-read]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/packages/coding-agent/src/web/firecrawl.ts
[o-installer]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/scripts/install.sh
[o-package]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/packages/coding-agent/package.json
[o-update]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/packages/coding-agent/src/cli/update-cli.ts
[o-search-doc]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/tools/web_search.md
[o-task-settings]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/packages/coding-agent/src/task/settings.ts
[o-agents]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/task-agent-discovery.md
[o-lsp]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/lsp-config.md
[o-browser]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/tools/browser.md
[o-eval]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/tools/eval.md
[o-task-approval]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/packages/coding-agent/src/task/index.ts#L726-L788
[o-computer]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/computer-use.md
[o-mcp]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/mcp-config.md
[o-memory-settings]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/packages/coding-agent/src/memory-backend/settings.ts
[policy-anthropic]: https://code.claude.com/docs/en/legal-and-compliance
[policy-google-cli]: https://github.com/google-gemini/gemini-cli/blob/main/docs/resources/tos-privacy.md
[policy-antigravity]: https://antigravity.google/terms
[policy-codex]: https://developers.openai.com/codex/auth

### Supplied upstream references

[p-home]: https://pi.dev/
[p-index]: https://pi.dev/docs/latest
[p-quickstart]: https://pi.dev/docs/latest/quickstart
[p-how]: https://pi.dev/docs/latest/how-pi-works
[p-usage]: https://pi.dev/docs/latest/usage
[p-models]: https://pi.dev/docs/latest/models
[p-sessions]: https://pi.dev/docs/latest/sessions
[p-security]: https://pi.dev/docs/latest/security
[p-llama]: https://pi.dev/docs/latest/llama-cpp
[p-terminal]: https://pi.dev/docs/latest/terminal-setup
[p-shell]: https://pi.dev/docs/latest/shell-aliases
[p-tmux]: https://pi.dev/docs/latest/tmux
[p-configuration]: https://pi.dev/docs/latest/configuration
[p-model-catalog]: https://pi.dev/models
[p-packages]: https://pi.dev/packages
[p-codemode]: https://pi.dev/docs/latest/codemode
[p-cli]: https://pi.dev/docs/latest/cli
[p-slash]: https://pi.dev/docs/latest/slash-commands
[p-model-config]: https://pi.dev/docs/latest/models-configuration
[p-env]: https://pi.dev/docs/latest/environment-variables
[p-format]: https://pi.dev/docs/latest/session-format
[p-compaction]: https://pi.dev/docs/latest/compaction
[p-sdk]: https://pi.dev/docs/latest/sdk
[p-cli-integration]: https://pi.dev/docs/latest/cli-integration
[p-tui]: https://pi.dev/docs/latest/tui
[p-virtual]: https://pi.dev/docs/latest/virtual-models
[p-custom]: https://pi.dev/docs/latest/custom-provider
[p-extensions]: https://pi.dev/docs/latest/extensions

## 15. Final adoption phase: selected public plugins, then standalone skills

Run this phase **after the core acceptance matrix passes and its state has been backed up**. Adopt the plugin layer first. Install standalone supplements last, after accepting that layer. Registration, download, installation, enabling a component, and validating its behavior are separate steps.

The public-only requirement takes precedence over the earlier machine inventory. Do not copy existing Claude/Copilot registries, credentials, whole skill directories, or plugin caches into OMP. Exclude Adobe-owned sources, internal hosts, organization-specific skills, and transitive components that require those systems. A public marketplace can advertise unrelated plugins: registration is not permission to install them.

The pasted standalone groups contain **102 requested names**, rather than the old headings' 67/41 totals: 62 shared, 37 Copilot-only, and 3 Claude-only. One requested personal item is Adobe-internal and is excluded. Of the remaining 101 names, **100 have located public payloads; one stays deferred because its public source revision is unresolved**. The omitted Scout and service/Git groups are not added back. These counts describe requested capabilities, not new copies: several already come from the selected plugins.

### 15.1 Sources and canonical plugin selection

OMP reads `.omp-plugin/marketplace.json`, falling back to `.claude-plugin/marketplace.json`. Its native user-scope marketplace registry is profile-aware and does not require enabling Claude's user registry. Use the catalog's plugin IDs exactly.

| Public source | Marketplace | Selected plugin IDs |
|---|---|---|
| [langchain-ai/langsmith-skills][public-langsmith] | `langsmith-skills` | `langsmith-skills@langsmith-skills` |
| [wshobson/agents][public-workflows] | `claude-code-workflows` | `c4-architecture@claude-code-workflows`, `code-documentation@claude-code-workflows`, `documentation-generation@claude-code-workflows`, `documentation-standards@claude-code-workflows` |
| [anthropics/claude-plugins-official][public-official] | `claude-plugins-official` | `claude-code-setup@claude-plugins-official`, `claude-md-management@claude-plugins-official`, `code-review@claude-plugins-official`, `code-simplifier@claude-plugins-official`, `context7@claude-plugins-official`, `frontend-design@claude-plugins-official`, `mattpocock-skills@claude-plugins-official`, `playwright@claude-plugins-official`, `plugin-dev@claude-plugins-official`, `skill-creator@claude-plugins-official` |
| [zarazhangrui/frontend-slides][public-slides] | `frontend-slides` | `frontend-slides@frontend-slides` |
| [kepano/obsidian-skills][public-obsidian] | `obsidian-skills` | `obsidian@obsidian-skills` |
| [obra/superpowers-marketplace][public-superpowers-marketplace], which references [obra/superpowers][public-superpowers] | `superpowers-marketplace` | `superpowers@superpowers-marketplace` |

This is **six marketplace sources and 18 distinct plugin selections**. The user's list names Superpowers through two channels. Recommend one active copy from the maintainer's `superpowers-marketplace`; do not also install `superpowers@claude-plugins-official`. The inspected official catalog pins upstream Superpowers at a 7.0.0-era revision, while the maintainer's catalog advertises 7.0.2 through a floating source. Pin the selected upstream commit rather than trusting that advertised version.

Select the official `skill-creator` plugin as its canonical source. The installed personal and wiki-vendored `SKILL.md` copies matched that implementation in the inventory; do not add another standalone copy. Compare supporting assets at the selected revisions before deduplicating entire directories.

The inspected workflows plugins declare versions 1.0.1 (`c4-architecture`), 1.2.2 (`code-documentation`), 1.2.4 (`documentation-generation`), and 1.1.0 (`documentation-standards`); LangSmith declares 0.1.0, frontend-slides 2.1.0, and Obsidian 1.0.1. Some official plugins omit versions. These are research observations, not proof that the next download has the same contents.

Research snapshot references:

| Source checkout | Inspected commit |
|---|---|
| `langsmith-skills` | `13c168b28dbc3a7679e8f0358160063ad3329694` |
| `claude-code-workflows` | `7e2fb559cf4b824b27f1fec49fe88f7511066d26` |
| `claude-plugins-official` | `fa4eb54397ee2faccb6940512a19c017cb1337f3` |
| `frontend-slides` | `9906a34d640d2111f724544cbc50f7f130569ae1` |
| `obsidian-skills` | `3ccff5338ea700537839b21900aa5358a0402c98` |
| `superpowers-marketplace` | `5c9072877417873fee42be1805aa776a453ec394` |
| External `obra/superpowers` | `22f0b463e7a5e579904dd6211a520321035526f7` |
| Public Matt Pocock supplement source | `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d` |

These are candidates for the approved installation manifest, not an instruction to update the core OMP release. Preserve the official catalog's separately pinned external revision unless an explicit reviewed override selects another one.

### 15.2 Prepare reproducible sources before installing

Maintain a non-secret adoption manifest outside OMP's runtime credential stores. For each selected plugin/skill, record its public repository URL, exact commit or package version, upstream-relative path, license/attribution, content hash, intended components, resolved OMP name, prerequisites, and disposition: `approved`, `needs-adaptation`, or `deferred`. A skill installer's folder hash is not a Git commit.

Use reviewed public checkouts under a dedicated source root, for example:

```bash
export OMP_PROFILE=personal
PUBLIC_SOURCES="$HOME/.local/share/omp-public-sources/personal"
mkdir -p "$PUBLIC_SOURCES"
```

Clone each source from the HTTPS URL in section 15.1, review its resolved commit, then check out that approved commit detached before adding it. Example pattern, with `APPROVED_SHA` supplied by the reviewed manifest:

```bash
git clone --filter=blob:none https://github.com/langchain-ai/langsmith-skills.git \
  "$PUBLIC_SOURCES/langsmith-skills"
git -C "$PUBLIC_SOURCES/langsmith-skills" checkout --detach "$APPROVED_SHA"
```

These command blocks share an operator-controlled shell. Re-establish `PUBLIC_SOURCES`, `APPROVED_SHA`, and later `APPROVED_SKILLS` explicitly after opening a fresh shell; require a full reviewed commit for `APPROVED_SHA` before running checkout commands.

Do not overwrite an existing checkout, choose `main` as an implicit permanent pin, or edit OMP's cached plugin trees. A pinned marketplace does not pin an external plugin unless its entry supplies a pinned `sha`/`ref`. Resolve and review external Matt Pocock/Superpowers sources separately. Where an upstream catalog floats an external source, prepare an approved local catalog with the same marketplace identity and the selected entry's exact source SHA before installing; retain the upstream catalog and the small reviewed catalog delta for updates.

Never commit `agent.db`, `.env`, provider credentials, or OMP's `omp-plugins.lock.json` as the adoption manifest. That runtime lockfile can contain plugin settings marked secret.

### 15.3 Register and install through OMP, not another harness

Close running model sessions during adoption so a partially prepared plugin set cannot become active. Confirm the selected profile, turn automatic marketplace updates off, then add the reviewed local catalogs:

```bash
omp config path
omp config set marketplace.autoUpdate off
omp plugin marketplace add "$PUBLIC_SOURCES/langsmith-skills"
omp plugin marketplace add "$PUBLIC_SOURCES/claude-code-workflows"
omp plugin marketplace add "$PUBLIC_SOURCES/claude-plugins-official"
omp plugin marketplace add "$PUBLIC_SOURCES/frontend-slides"
omp plugin marketplace add "$PUBLIC_SOURCES/obsidian-skills"
omp plugin marketplace add "$PUBLIC_SOURCES/superpowers-marketplace"
omp plugin marketplace list
```

The directory basenames above are the chosen checkout locations; the catalog's `name` defines marketplace identity. Register only the six reviewed catalogs. Do not transfer other entries from the machine inventory.

For each exact plugin ID in section 15.1, preview, inspect its source/components, then install only when its component gate passes:

```bash
omp plugin install --dry-run --scope user langsmith-skills@langsmith-skills
omp plugin install --scope user langsmith-skills@langsmith-skills
omp plugin list --json
omp plugin doctor
```

Repeat that pattern for the other approved IDs. `--scope user` means the active OMP profile's user plugin registry, not a repository install or Claude's registry. `--dry-run` validates cached catalog/scope constraints; it does not fetch plugin code, run a compatibility test, or guarantee safety. Marketplace add/update/enable/disable do not support dry-run. Do not use `--force`, `--yes`, `pkg[*]`, or an all-marketplace install.

Installation does not authorize executable components. Inventory native plugin roots and the effective component loadout before starting a model session. OMP has no documented universal “install this Claude plugin's skills but quarantine everything else” flag; do not invent one. If a stock package cannot meet the component policy, leave it disabled or defer that component. A reviewed local skills-only derivative is a separate adaptation, with its source delta and license retained, not an unmodified upstream install.

After filesystem/catalog changes, `/reload-plugins` refreshes skills, commands, agents, and MCP discovery. Newly installed non-MCP tools, hooks, and extension modules need a restart. Validate in a disposable repository before moving back to normal work. Do not treat successful reload as acceptance.

### 15.4 Component gates and prerequisites

OMP can discover Claude-format skills, commands, and agents, including manifest-declared skill directories. That addresses packaging; the content's tool calls, models, hooks, and side effects still need validation.

| Selection | Source layout and required work |
|---|---|
| LangSmith | Manifest points at `config/skills/`, not root `skills/`. Confirm all selected skills resolve there. Trace/dataset/evaluator workflows need the public `langsmith` CLI and authorized `LANGSMITH_API_KEY`; `LANGSMITH_PROJECT` and `LANGSMITH_WORKSPACE_ID` depend on the account/workflow. Record/pin the CLI separately. Do not enable tracing or send repository/session data merely by installing instructions. Optional provider API keys are separate billing decisions |
| C4 architecture | Agent/command package, not a standalone skill pack. Confirm the four C4 agent definitions and the command resolve through OMP's `/agents` and command menu |
| Code/documentation generation | Check overlapping agent/command names before enabling both packages. Use observed OMP names and explicit model overrides; do not assume Copilot/Claude namespace strings or `model: sonnet` select an available OMP model |
| Documentation standards | Public HADS/grounded-vault skills under the workflows marketplace; preserve the component authors' attribution rather than assuming every entry has the marketplace owner's authorship |
| Claude setup / CLAUDE.md management | Instructions target Claude configuration. Treat them as reference workflows until their output targets are adapted to OMP; do not let an OMP session rewrite the existing Claude/Copilot environment as a side effect |
| Code review / code simplifier | Review is a command package and simplifier is an agent package. Map actual tools/models and preserve the writer-approval/isolation policy; neither name makes the component read-only |
| Frontend design / slides | Preserve the complete skill assets/references and any rendering scripts. Keep generated output in a disposable project for the smoke test; installing instructions does not approve executing scripts |
| Matt Pocock | Official catalog references the public `mattpocock/skills` repository. The inspected plugin enumerates 27 nested skill paths, covering 26 requested standalone names. Ten more requested names exist outside that manifest; one requested name is absent from the inspected repository. Follow the exact supplement/defer split below rather than installing the whole repository twice |
| Obsidian | Public `kepano/obsidian-skills` plugin, distinct from `obsidian-wiki`. Some skills need an Obsidian installation/CLI or optional Defuddle/knap utilities. Confirm the target platform and exact executable before use; no vault path or write authorization is implied |
| Plugin development | Includes skills, commands, and agent definitions that describe Claude's plugin contracts. Use for OMP only after reviewing the different marketplace/discovery/runtime contracts; do not generate invalid OMP artifacts from Claude-only templates |
| Skill creator | Use one official skill plus its supporting assets/scripts. Eval runners and model calls require their own dependencies and approval; package discovery alone is not a successful eval |
| Superpowers | Preserve the skills; do not execute or translate its Claude `SessionStart` hook automatically. The inspected package includes `hooks/hooks.json` with Claude-specific dispatch. OMP's legacy plugin hook discovery scans `hooks/pre`/`hooks/post`; that does not make `SessionStart` wiring portable. Verify the complete installed entry points and use an explicit skill invocation or a separately reviewed OMP-native integration |
| Context7 | MCP server capability, not a skill. Verify the public hosted endpoint and optional key configuration. Treat documentation queries as outbound data |
| Playwright | MCP server capability, distinct from the final `playwright-cli` skill. Pin the server package/runtime and approve browser dependencies. Choose native OMP browser, this MCP, or the CLI explicitly per workflow; avoid several indistinguishable browser tool surfaces |

For imported agents, use `/agents` to inspect the effective model and tools. OMP's separate task-agent discovery loads `agents/` from native marketplace installs even when foreign Claude user discovery is off; inspecting only `claude-plugins.ts` would miss that path. It drops Claude-dialect `model` frontmatter rather than interpreting `sonnet`/`opus` as OMP selectors. Configure `task.agentModelOverrides` using the exact discovered agent names and authorized model selectors before invoking them. Agents use first-wins dedup by exact name, so verify the winner where documentation packages overlap. OMP worker `yolo` behavior, explicit prompt policies, and writer isolation remain unchanged.

Before installing MCP wrappers, inspect their `.mcp.json` files and place their exact discovered names in the active profile's `mcp.json` `disabledServers`. Native Claude-format plugin servers use `<plugin>:<server>` names. Disable entries **before** the next session can connect; `mcp.enableProjectConfig: false` does not disable user plugin MCP servers. Enable only the reviewed server/endpoint after its prerequisites and data flow are approved. Never put API key values into this spec or a shell argument.

The inspected wrappers resolve as `context7:context7` and `playwright:playwright`. Merge this denylist into the existing active-profile MCP configuration before installing those wrappers, without overwriting other reviewed entries:

```json
{
  "mcpServers": {},
  "disabledServers": ["context7:context7", "playwright:playwright"]
}
```

Context7's inspected wrapper uses `https://mcp.context7.com/mcp?client=claude-code-plugin` and declares no header mapping for `CONTEXT7_API_KEY`, despite its README mentioning automatic key pickup. Do not assume exporting that variable authenticates this HTTP client. Use [Upstash's supported client configuration][public-context7-clients] for any explicit auth override, keep values private, and test the resulting account/rate-limit behavior before removing the denylist entry. Do not run `ctx7 setup` against another harness as an OMP configuration shortcut.

Playwright's inspected wrapper runs `npx` with `@playwright/mcp@latest`. Node.js 18+ is a server prerequisite. Before enabling it, use an approved exact `@playwright/mcp` version through an OMP-native override for the same namespaced server, or another reviewed pinned configuration; do not silently execute `@latest` on startup. Inspect browser downloads, profile storage, and network access. The [Microsoft server README][public-playwright-mcp] distinguishes this persistent MCP workflow from its separate CLI/skills workflow.

Sources: [OMP marketplace contract][o-marketplace], [plugin CLI][o-plugin-cli], [native Claude-format discovery][o-plugin-discovery], [MCP configuration][o-mcp], and the public repositories in section 15.1.

### 15.5 Accept the plugin layer before adding loose skills

Record which of the 18 selections passed, which need a documented adaptation, and which remain deferred. Registration/install counts are not a substitute for these checks:

- The resolved source, component paths, versions/commits, and public ownership match the adoption manifest. No excluded component or broad foreign user registry appears in the effective loadout.
- `/agents`, the command menu, `omp skill list --json`, and `/mcp list` show the expected distinct components. LangSmith's nonstandard skill root and Matt Pocock's explicit nested paths resolve.
- Only one Superpowers and one canonical skill-creator are active. Name collisions between documentation packages, review workflows, and plugin versus loose Matt Pocock skills have an explicit winner.
- A disposable skill/command invocation works with actual OMP tools and the authorized model. No unsupported Claude hook, unexpected cloud upload, unpinned browser download, or unattended writer starts.
- Staged MCP servers remain disabled until enabled individually. Repeat the profile/approval/search acceptance checks after enabling a component.

If a component fails, disable or uninstall its exact ID using OMP's user-scope command, restart when required, and restore the core snapshot if necessary. Keep a failure explicit; do not mark the entire requested ecosystem installed because the catalog accepted its names.

### 15.6 Standalone skills: selected public sources

This is the **last installation stage**. All names below remain requested capabilities, subject to dependencies and OMP tests. Prefer an already accepted plugin's copy; do not install a second copy just to reproduce the standalone inventory.

| Public source | Selected names | Adoption rule |
|---|---|---|
| [mattpocock/skills][public-matt] | `ask-matt`, `claude-handoff`, `code-review`, `codebase-design`, `diagnosing-bugs`, `domain-modeling`, `git-guardrails-claude-code`, `grill-me`, `grill-with-docs`, `grilling`, `handoff`, `implement`, `implement-spec`, `improve-codebase-architecture`, `loop-me`, `migrate-to-shoehorn`, `prototype`, `research`, `retro`, `scaffold-exercises`, `setup-matt-pocock-skills`, `setup-pre-commit`, `setup-ts-deep-modules`, `tdd`, `teach`, `to-questionnaire`, `to-spec`, `to-tickets`, `triage`, `wait-what`, `wayfinder`, `wizard`, `writing-beats`, `writing-for-agents`, `writing-fragments`, `writing-shape` | 36 located names. Use the accepted plugin's 26 matching copies first, then the ten exact public supplements below. Verify scripts/harness assumptions before invoking them |
| [manaflow-ai/cmux][public-cmux] | `cmux`, `cmux-browser`, `cmux-capture`, `cmux-cloud-vm`, `cmux-cua`, `cmux-custom-sidebar`, `cmux-customization`, `cmux-diagnostics`, `cmux-keyboard-shortcuts`, `cmux-markdown`, `cmux-settings`, `cmux-workspace` | 12 names under `skills/`. Native cmux app/CLI needs macOS; do not promise it on a Linux-only host. Retain subtree license/attribution and review the repository's license carve-outs before redistribution. Keep `cmux-cua` out of automatic invocation; OMP visibility metadata is not a desktop-permission boundary |
| [marimo-team/skills][public-marimo-skills] | `add-molab-badge`, `anywidget-generator`, `auto-paper-demo`, `implement-paper`, `implement-paper-auto`, `jupyter-to-marimo`, `marimo-batch`, `marimo-notebook`, `streamlit-to-marimo`, `wasm-compatibility` | 10 names. Requires the selected workflow's `uv`/marimo environment; notebook/browser/WASM execution is a separate prerequisite and approval |
| [marimo-team/marimo-pair][public-marimo-pair] | `marimo-pair`, `retro-marimo-pair` | Both live under `skills/<name>/SKILL.md`. Preserve their reference trees; requires a running marimo notebook server plus `bash`, `curl`, and `jq`. Use authenticated server access where available rather than exposing a tokenless server |
| [herdrdev/herdr][public-herdr] | `herdr` | Requires the Herdr terminal/runtime on a supported host. Confirm Linux support before enabling execution there |
| [vercel-labs/skills][public-skills-cli] | `find-skills` | Exact public file: `skills/find-skills/SKILL.md` in this repository. It also ships with npm package `skills`. Do not substitute `vercel-labs/agent-skills` from a generic installer example or invent an OMP-specific installer target |
| [microsoft/playwright-cli][public-playwright-cli] | `playwright-cli` | Exact public file: `skills/playwright-cli/SKILL.md`; npm package is `@playwright/cli`, executable `playwright-cli`, Apache-2.0. Current local and upstream revisions differ, so pin and test the chosen revision |
| [Ar9av/obsidian-wiki][public-wiki] / [PyPI distribution][public-wiki-pypi] | `claude-history-ingest`, `codex-history-ingest`, `copilot-history-ingest`, `cross-linker`, `daily-update`, `graph-colorize`, `hermes-history-ingest`, `impl-validator`, `llm-wiki`, `memory-bridge`, `openclaw-history-ingest`, `pi-history-ingest`, `tag-taxonomy`, `vault-skill-factory`, `wiki-agent`, `wiki-capture`, `wiki-context-pack`, `wiki-dashboard`, `wiki-dedup`, `wiki-digest`, `wiki-export`, `wiki-history-ingest`, `wiki-import`, `wiki-ingest`, `wiki-lint`, `wiki-query`, `wiki-rebuild`, `wiki-research`, `wiki-setup`, `wiki-stage-commit`, `wiki-status`, `wiki-switch`, `wiki-synthesize`, `wiki-update` | 34 wiki-owned names. Use one global uv tool installation with the approved `graph,ast` extras and one explicit vault decision. Do not run ingestion or install cross-harness session hooks during onboarding |
| [Official skill creator][public-official] | `skill-creator` | Satisfy through the accepted plugin; no additional wiki-vendored or personal copy |
| [zarazhangrui/codebase-to-course][public-course] | `codebase-to-course` | Public upstream for the local skill. Preserve referenced assets and review license/use terms before copying or redistributing it |
| [hardikpandya/stop-slop][public-stop-slop] | `stop-slop` | Use the public upstream skill and license, not a copy pulled from a mixed organization-specific root |

The rows contain 100 located public-source candidates. They do not include the internal item, the omitted groups, or the unresolved name below. Provenance is not an OMP certification: report platform-specific deferrals and failed tool mappings individually.

**Deferred, not installed:** `resolving-merge-conflicts`. The local skill receipt attributes it to `mattpocock/skills`, but the file is absent from the inspected public commit `4ae2317d`. Require a verified public historical revision or another explicitly approved public source before adding it. Do not copy its local body from the existing machine or silently substitute another skill.

For Matt Pocock, the plugin's 27-entry declared list includes 26 of the requested names; its additional `pr` belongs to the selected plugin bundle, not a new standalone request. Only these ten requested public files need loose supplementation:

| Upstream parent directory at `4ae2317d` | Supplement directories, each containing `SKILL.md` |
|---|---|
| `skills/in-progress/` | `claude-handoff`, `loop-me`, `setup-ts-deep-modules`, `writing-beats`, `writing-fragments`, `writing-shape` |
| `skills/misc/` | `git-guardrails-claude-code`, `migrate-to-shoehorn`, `scaffold-exercises`, `setup-pre-commit` |

`implement-spec` and `retro` exist under `skills/engineering/` and are declared by the inspected plugin; do not reproduce the older personal receipt's `in-progress` paths for them. The repository also contains unrequested `chief-of-staff` and `software-factory` skills; their presence is not approval to add them.

### 15.7 Install only approved final supplements

Use pinned public checkouts and complete skill directories, not an entire home-directory skill root. `omp skill install` targets OMP's Skillshare registry packages; it is **not** a documented installer for arbitrary GitHub skill URLs. `omp skill import` publishes a `.skill` archive to that registry; it is not the local-import command for this task. Do not use either to guess installation routes.

For reviewed source-backed skills that the accepted plugins do not already provide, create one approved-only root and link each selected complete skill directory. Example for one macOS skill, after validating the source checkout:

```bash
APPROVED_SKILLS="$HOME/.omp/profiles/personal/agent/approved-skills"
mkdir -p "$APPROVED_SKILLS"
ln -s "$PUBLIC_SOURCES/cmux/skills/cmux-browser" \
  "$APPROVED_SKILLS/cmux-browser"
omp config set skills.customDirectories \
  '["~/.omp/profiles/personal/agent/approved-skills"]'
omp skill list --json
```

Resolve each skill's real upstream path from its source manifest, not from its display name. Do not overwrite an existing destination or copy only `SKILL.md`; helper scripts, references, licenses, and relative links must survive. OMP scans one level below each custom root. A custom-directory skill can outrank a plugin skill, so omit duplicates rather than relying on shadowing.

For wiki prerequisites, the inventory's installed version was 2026.7.3. Use an approved pin such as:

```bash
uv tool install "obsidian-wiki[graph,ast]==2026.7.3"
```

Reuse a matching existing uv installation rather than installing it again. Resolve the package's shipped `_data/skills` with its managed Python:

```bash
WIKI_PY="$(uv tool dir)/obsidian-wiki/bin/python"
"$WIKI_PY" -c 'from importlib.resources import files; print(files("obsidian_wiki").joinpath("_data", "skills"))'
```

Expose only the 34 selected wiki-owned skill directories from that result; do not hardcode a Python minor-version path or assume current upstream `main` contains the same inventory as the pinned package. `obsidian-wiki setup` has no `--agent`/`--agents` selector, and it can add Claude session hooks unless `--no-hooks` is supplied. This plan skips `setup` while exposing skills; a separate vault-initialization decision must name its exact effects and target. Do not overwrite the vault configuration, ingest history, or enable hooks as a side effect.

For Playwright CLI, approve one exact npm release before installing:

```bash
npm install -g "@playwright/cli@$APPROVED_PLAYWRIGHT_CLI_VERSION"
playwright-cli --help
```

Resolve `APPROVED_PLAYWRIGHT_CLI_VERSION` from the reviewed package manifest/release, not `latest`. Upstream documents `playwright-cli install --skills`; do not run that broad skill installer against the current repository or other harnesses for this task. Expose the reviewed `skills/playwright-cli` folder through the approved-only OMP root instead, and approve browser/dependency installation separately. The CLI and MCP server have different packages and version pins.

Use the same pinned-checkout/link method for the two marimo-pair skills, `find-skills`, `codebase-to-course`, and `stop-slop`. For each remaining source group, verify its actual upstream skill directories and required runtime before linking only the selected names. General `npx skills add <repo>` commands can modify shared/other-harness roots; they are not the default OMP-only adoption route.

Keep `skills.enableClaudeUser`, `skills.enableClaudeProject`, `skills.enableCodexUser`, `skills.enableAgentsUser`, and `skills.enableAgentsProject` false as in the candidate. Do not opt foreign registries back in to fix a missing skill. Build an exact `skills.includeSkills` allowlist from the **approved final resolved names** after resolving plugin/standalone collisions; an empty allowlist means include everything and is not an exclusion policy. Name filtering is defense in depth: verify every resolved `filePath`/`baseDir` against the approved real source paths, since an unapproved copy can have a familiar name.

Finally, run `omp skill list --json` in a neutral directory and the target repository. Check requested-name coverage, warnings, final invocation names, real source paths, blocked-source absence, required executables, and assets. Smoke-test one benign task per adopted source group without running history ingestion or changing a real vault. Keep unsupported-platform and unadapted skills deferred, with a reason. Record this layer separately so it can be removed without disturbing the accepted core or the existing Claude/Copilot installations.

[o-marketplace]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/docs/marketplace.md
[o-plugin-cli]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/packages/coding-agent/src/cli/plugin-cli.ts
[o-plugin-discovery]: https://github.com/can1357/oh-my-pi/blob/594670d6b0b6d5f8080693aad34dedd38b5ebd94/packages/coding-agent/src/discovery/claude-plugins.ts
[public-langsmith]: https://github.com/langchain-ai/langsmith-skills
[public-workflows]: https://github.com/wshobson/agents
[public-official]: https://github.com/anthropics/claude-plugins-official
[public-slides]: https://github.com/zarazhangrui/frontend-slides
[public-obsidian]: https://github.com/kepano/obsidian-skills
[public-superpowers-marketplace]: https://github.com/obra/superpowers-marketplace
[public-superpowers]: https://github.com/obra/superpowers
[public-matt]: https://github.com/mattpocock/skills
[public-cmux]: https://github.com/manaflow-ai/cmux
[public-marimo-skills]: https://github.com/marimo-team/skills
[public-marimo-pair]: https://github.com/marimo-team/marimo-pair
[public-herdr]: https://github.com/herdrdev/herdr
[public-skills-cli]: https://github.com/vercel-labs/skills
[public-playwright-cli]: https://github.com/microsoft/playwright-cli
[public-wiki]: https://github.com/Ar9av/obsidian-wiki
[public-wiki-pypi]: https://pypi.org/project/obsidian-wiki/2026.7.3/
[public-course]: https://github.com/zarazhangrui/codebase-to-course
[public-stop-slop]: https://github.com/hardikpandya/stop-slop
[public-claude-auth]: https://github.com/pankajudhas81/pi-claude-auth
[public-claude-cli]: https://pi.dev/packages/@saccolabs/pi-claude-cli
[public-context7-clients]: https://context7.com/docs/resources/all-clients
[public-playwright-mcp]: https://github.com/microsoft/playwright-mcp
