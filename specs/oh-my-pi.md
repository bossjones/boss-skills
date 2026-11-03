# oh-my-pi setup specification for macOS and Linux

Status: proposed configuration, pending approval. This document does not authorize installation, OAuth login, secret access, or changes to this machine.

Review pass: Gemini 4 Argon reported no significant issues. Opus 5.5 identified three non-blocking gaps: the Codex-only consequence, task-child authorization controls, and a consolidated configuration template. This revision addresses all three. These reviews do not replace the implementation acceptance checks.

Research date: 2026-11-03. Fork source baseline: [`can1357/oh-my-pi` at `594670d6`](https://github.com/can1357/oh-my-pi/tree/594670d6b0b6d5f8080693aad34dedd38b5ebd94), whose CLI package declares version `18.16.0`. Pi's `/docs/latest` and catalogs are rolling references. Recheck the selected release and its configuration schema before implementing.

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

**Recommendations below are author proposals, not choices the user has already approved.** Unanswered decisions remain in section 13. Implementation must wait for approval of this spec.

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

### Precedence and edit ownership

Settings resolve from low to high:

```text
defaults < global/profile YAML < project settings < config overlays < runtime overrides < declared setting environment variables
```

`PI_CONFIG_FILES` overlays load before explicit repeated `--config` files; later overlays win. Some declared environment variables act as fallbacks instead of overrides. API credential resolution follows a separate chain.

Mappings deep-merge. Arrays replace rather than append. A project `disabledProviders` array can therefore remove the global restrictions unless it repeats them. Native project settings are cwd-scoped, not nearest-ancestor settings. Discovered foreign settings have additional source-order behavior; do not rely on a global file as a mandatory policy boundary.

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

Do not patch client fingerprints, impersonate an approved client, reuse tokens from first-party applications, or evade provider restrictions.

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
| `image` / `speech` / `dictation` / `judge` | Optional generation and non-chat workloads | Configure only when adopting those features |

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

Per-tool rules, critical-command policies, Eval execution, browser control, MCP calls, and foreground desktop acquisition have separate behavior. Do not approve `bash` broadly and assume `eval` cannot execute the same command. Restricted folders do not parse paths embedded in shell text and do not provide filesystem containment.

Opening a project can load executable inputs before a model tool approval appears. Review project `.omp`, foreign-agent configuration, hooks, tool modules, plugins, and MCP definitions before launching. Use an external container/VM or dedicated account for untrusted repositories. A profile, workspace clone, Git worktree, restricted-folder list, or read-only prompt is not a substitute.

For narrowing an invocation, OMP documents `--no-extensions` and exact `--trusted-extension` paths. A nested YAML overlay containing `mcp.enableProjectConfig: false` excludes project-level MCP sources, including foreign project formats, but not user-level MCP sources. `--no-tools` does not suppress separately discovered project tool modules. Do not advertise these switches as a complete “safe mode.”

### Subagents and advisors

Use built-in `task` for independent work; enable `task.structured` for typed yields. The candidate limits concurrency to two, allows isolation, and disables automatic application of isolated changes.

`task.isolation.enabled` permits per-item `isolated: true`; it does not force every worker into isolation. Require that flag for concurrent writers and inspect the resulting patch/branch before integration. Isolation is unavailable for plan-mode workers.

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
  web: web/tavily
defaultThinkingLevel: medium
enabledProviders: []
disabledProviders:
  - anthropic
  - google-gemini-cli
  - google-antigravity
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

`disabledProviders` blocks the restricted subscription routes; it also blocks Anthropic API access until that provider entry is removed as part of approving a different access method. Empty `enabledProviders` keeps foreign user discovery opt-in; native and `.agents` sources still need inspection. Project MCP and the browser start off in this candidate, so enabling either after review is an explicit configuration change. Read-only research can still use native URL reading/search.

`modelFallback` governs chat failover; search follows its own configured chain. Review any existing per-model fallback entries too. Adopt a [memory backend][o-memory-settings] and automatic learning only after deciding retention, model use, and source scope. A question timeout must not select a recommended answer in place of a user decision.

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

Recommend starting with native OMP preferences plus the reviewed project's existing instructions and selected skills. In this repository, `plugins/` remains the source of truth; `.claude/skills` contains dogfooding mirrors. Do not duplicate those skills under `.omp`.

If importing a skill root through `skills.customDirectories`, point at a directory whose immediate children contain `SKILL.md`; nested category trees are not scanned recursively. Example for this checkout, after approving the scope:

```yaml
skills:
  customDirectories:
    - /absolute/path/to/boss-skills/.claude/skills
```

Resolve the real path during implementation; do not commit a machine-specific absolute path as a portable default. Symlink/identical-content dedup and precedence can change the visible names. Confirm which source supplies each skill.

Both `AGENTS.md` and `CLAUDE.md` have discovery support, but do not assume same-directory files concatenate. OMP keeps one project context file per directory depth according to provider priority. Avoid adding another copy of this repository's generated policy.

Use the discovered `/skill:<name>` command, or the resolved namespaced form shown by OMP. Do not promise Claude plugin syntax such as `/meta-docs:unslop` names an OMP skill. Reading a skill's instructions does not provide Claude-only hooks, Copilot tools, or an executable the skill expects.

### MCP and source inventory

OMP has built-in MCP support and imports configuration from other ecosystems. Inventory server names, scope, transport, executable/endpoint, tool names, and auth method without printing keys. For Scout, reuse the existing authorized server definition if the user approves it; do not invent a remote endpoint or duplicate a search service.

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

Catalog descriptions and download counts are not evidence of code review or compatibility. Before adding a package, record its purpose, repository, exact version/commit, license, dependencies/install scripts, tool/command collisions, data recipients, OMP API compatibility, and removal procedure. Test one package at a time in a separate profile/disposable repository. Keep the approved baseline free of redundant extensions, without disabling OMP's bundled capabilities to imitate upstream Pi.

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
2. **Inventory without secrets.** Inspect OS/architecture, executable paths, tool versions, terminal/shell, reviewed config-source names, and existing installations. Do not read credential values. Record any existing OMP state before migration-capable commands run.
3. **Snapshot and install.** Back up affected settings/state with appropriate permissions. Install the selected pinned release through one manager. Confirm `command -v omp`, version, and help.
4. **Create policy before first project launch.** Configure the approved profile and explicit approvals in a neutral, reviewed directory. Add non-secret settings; do not run setup from an unreviewed repository.
5. **Authenticate permitted providers.** Log in separately using OMP. Confirm selected workspace/account, model visibility, one small response, and one tool-using response. Record quota/errors without token values.
6. **Assign roles and search.** Replace the candidate's model placeholder, configure the approved search chain, and compare `omp config list --json` with every intended template value in the target repository. Check `retry.fallbackChains.web` equals the approved list, not an inherited/default chain; check per-tool prompt policies, disabled routes, and both isolation flags. Record mismatches and resolve their precedence before continuing.
7. **Adopt bundled workflows.** Exercise read-only task delegation/Agent Hub first, then an isolated writing task and explicit patch review. Test advisor only if approved. Add LSP for a real project and optional DAP/browser dependencies as required.
8. **Load selected content.** Verify instruction provenance, skill names/collisions, MCP inventory, imported agent toolsets, and plugin/hook compatibility. Do not broaden foreign discovery to fix a missing skill without reviewing the consequences.
9. **Exercise terminal and persistence.** Test active keybindings, a normal restart/resume, compaction, working-directory behavior, and optional multiplexer placement without killing existing sessions.
10. **Hand over a manifest and rollback path.** Save non-secret settings, versions, accepted decisions, unresolved caveats, and observed outcomes. Leave optional packages/features disabled or unconfigured as agreed.

### Acceptance matrix

| Area | Evidence required |
|---|---|
| Installation | One installation owner; expected executable/version on both target platforms, or a clear platform-specific blocker |
| Configuration | Effective registered settings match the intended profile and project; no ignored/invalid-key warnings |
| OAuth | Every permitted provider completes a real response/tool round trip; prohibited/unauthorized providers remain unused |
| Models | Exact provider/model selectors and resolved role assignments recorded; no unintended API-key or cross-provider fallback |
| Search | Independent Tavily/Brave/Firecrawl probes; selected backend and citations visible; controlled fallback failure case |
| Keyless boundary | Search-only behavior confirmed where available; no claim that unauthenticated scraping works |
| Approval | Denied harmless test action does not execute; parent behavior matches approved mode; user understands child `yolo` authorization and inherited denies |
| Workers | Read-only delegation returns evidence; each task/batch requires approval; a headless shell/Eval probe fails under explicit prompt policy; isolated file changes wait for patch acceptance |
| Discovery | Expected context/skills present once; source provenance known; no unintended MCP/hook launch |
| Dependencies | Missing LSP/DAP/Eval/browser prerequisites produce a specific blocker, not silent global installation |
| Sessions | Resume restores expected cwd/model; compaction preserves needed context; no export/share upload |
| Secrets | No values in committed files, recorded output, shell history, screenshots, or handover; private state/backup permissions established |
| Upgrade recovery | Previous installation reference and consistent state snapshot available; schema migration consequences documented |

Do not deliberately rotate tokens, exhaust subscription quotas, break a production workspace, or invoke a consequential command to test the setup.

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
| Start with a native `personal` profile? | Yes | Default profile | Profile name/layout |
| Start with `always-ask` instead of the default `yolo`? | Yes | `write` for trusted coding, after reviewing execution gates | Approval policy |
| Accept Codex-only chat inside OMP and keep Claude/Gemini subscriptions in first-party tools? | Yes, after confirming Codex authorization | Approve adding paid Anthropic Console/Gemini API or a supported cloud-provider route; otherwise keep the affected work outside OMP | Authorized access method and billing limits |
| Use the same verified Codex model across initial chat roles? | Yes; advisor remains off | Choose other available authorized models; cross-family advisor needs another access method | Exact role preferences |
| Use Tavily → Brave → Firecrawl for public search? | Yes | Another explicit order or OAuth-grounded primary | Search policy |
| Keep automatic cross-provider chat failover off initially? | Yes | Approve a named data/usage failover chain | Allowed routes |
| Start with at most two workers and deliberate advisor activation? | Yes | Different concurrency or advisor cadence | Limits/model choice |
| Require approval for every task batch and block headless shell/Eval/browser calls initially? | Yes | Approve a separately designed worker execution policy, preferably inside external isolation | Agent/tool authorization model |
| Reuse reviewed project instructions and selected skills, without wholesale user-config import? | Yes | Approve specific foreign source roots and their executable inputs | Import scope |
| Defer desktop control, collaboration uploads, local weights, and telemetry packages? | Yes | Adopt a named capability with its prerequisites and data policy | Feature selection |

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
