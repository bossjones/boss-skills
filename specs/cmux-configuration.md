# Plan: Optimize cmux configuration (Ghostty config + cmux.json + Claude Code integration)

> Deliverable spec. Implement with `agent-harness:build`. This document does **not** modify any config itself.

## Context

The user runs cmux (`/Applications/cmux.app`) as their primary terminal and drives it hard
with Claude Code / multi-agent workflows (cmux-team). They asked for the "best settings"
based on three community write-ups + the official docs:

- cmux docs — https://cmux.com/docs/configuration
- Issue #1657 "optimized ghostty config for cmux" — https://github.com/manaflow-ai/cmux/issues/1657
- gordonbeeming "cmux migration from Ghostty" — https://gordonbeeming.com/blog/2026-04-24/cmux-migration-from-ghostty
- subaud.io "building my terminal setup" — https://www.subaud.io/building-my-terminal-setup/

**What exploration found (the problem):**

1. **No active Ghostty config exists.** cmux is built on libghostty and reads
   `~/.config/ghostty/config` (no extension) directly — this is the single biggest lever every
   blog post agrees on. The user only has `~/.config/ghostty/config.ghostty` (0 bytes), which
   Ghostty/cmux **does not read**. So cmux is running entirely on built-in defaults: default
   font, default theme, Ghostty's own tab bar showing redundantly next to cmux's, no split
   dimming, no padding tuned for the sidebar.

2. **`~/.config/cmux/cmux.json` is 100% commented out** (the launch template). Every cmux app
   setting silently falls back to whatever is stored in the Settings window — nothing is
   file-managed, explicit, or version-controllable.

3. **Font reality:** the blog authors' fonts (Monaspace, MonoLisa) are **not installed**.
   Installed Nerd Fonts: JetBrainsMono, FiraCode, Hack. Decision → **JetBrainsMono Nerd Font**.

**Intended outcome:** two authoritative, commented, version-controllable config files plus a
Claude Code notification bridge, so cmux looks and behaves the way the community-optimized
setups do and the config is reproducible on any machine.

## Objective

When complete, the user will have:
- A real `~/.config/ghostty/config` tuned for cmux (font, catppuccin theme, tab bar off,
  split dimming, sidebar-friendly padding, sane macOS + terminal behavior).
- A curated, explicitly-set `~/.config/cmux/cmux.json` (app / terminal / sidebar / automation /
  notifications / browser) instead of an all-commented template.
- Claude Code events surfaced through cmux notifications (pane flash + Dock badge).
- A clean removal of the dead `config.ghostty` stub.

## Problem Statement

cmux's best features (agent-focused split dimming, the git/PR/ports sidebar, native theming,
the notification system) are only realized when its Ghostty config and `cmux.json` are actually
populated. The user currently has neither — an empty misnamed Ghostty file and a template-only
cmux.json — so cmux runs on generic defaults and none of the settings are captured as code.

## Solution Approach

Author two config files from the union of the four sources, constrained to **keys verified
against the real `cmux.json` template** (authoritative for cmux keys) and standard Ghostty keys.
Split-inherit / blur / glass values that only appear in one blog post are included but flagged
`# verify` so `build` confirms cmux accepts them on reload rather than trusting a single source.
The Claude Code notification bridge needs **no wiring**: `cmux hooks --help` confirms *"Claude
Code hooks are injected automatically by the cmux Claude wrapper,"* and Claude is intentionally
absent from the manual `cmux hooks setup` agent list. So the plan keeps `claudeCodeIntegration:
true` and adds nothing to `~/.claude/settings.json`; a `CMUX_SURFACE_ID`-guarded `cmux notify`
hook (verified flags `--title/--subtitle/--body`) is documented only as an opt-in for *custom*
message text, with an explicit duplicate-notification warning. Validation and reload use cmux's
own tooling (`cmux config doctor`, `cmux reload-config`) rather than hand-rolled parsing. Keep
security-sensitive settings (socket control mode) at their safe defaults and call that out.

## Relevant Files

- `~/.config/ghostty/config` — **new file**; read directly by cmux (libghostty). The primary
  surface for font/theme/window/split/macOS behavior.
- `~/.config/cmux/cmux.json` — existing all-commented template; selectively populate. Real key
  namespaces (authoritative list, from the live template): `app`, `workspaceGroups`, `terminal`,
  `notifications`, `sidebar`, `workspaceColors`, `sidebarAppearance`, `automation`, `browser`,
  `markdown`, `fileEditor`, `fileExplorer`, `diffViewer`, `shortcuts`.
- `~/.config/ghostty/config.ghostty` — **dead 0-byte stub**; delete (it is not read by anything).
- `~/.claude/settings.json` (or `settings.local.json`) — **normally untouched.** Claude Code hooks
  are auto-injected by the cmux Claude wrapper (confirmed via `cmux hooks --help`). Edit only to add
  an **optional** custom-message `Stop` hook guarded on `CMUX_SURFACE_ID` — see Step 4 (and its
  duplicate-notification caveat).

### New Files
- `~/.config/ghostty/config`

### Reference (do not edit — context only)
- `.claude/skills/` cmux skills in this repo: `cmux-customization`, `cmux-settings`,
  `cmux-socket-policy`, `cmux-shared-behavior` — consult `cmux-socket-policy` before ever changing
  `automation.socketControlMode`.

## Implementation Phases

### Phase 1: Foundation — Ghostty config
Create `~/.config/ghostty/config` and remove the dead stub. This alone delivers ~80% of the
visible improvement (font, theme, tab bar, dimming, padding).

### Phase 2: Core Implementation — cmux.json
Replace the all-commented template with a curated, explicitly-set config for the namespaces that
matter to an agent-heavy workflow, leaving the rest commented (→ Settings fallback).

### Phase 3: Integration & Polish — Claude Code bridge + validation
Wire Claude Code notifications into cmux, reload config, confirm no keys are rejected, delete the
stub, and spot-check the sidebar/theme visually.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Back up existing config
- Copy `~/.config/cmux/cmux.json` → a **timestamped** `~/.config/cmux/cmux.json.<timestamp>.bak`
  before editing (cmux's own agent guidance in `cmux --help` says to keep a timestamped `.bak`).
- Note: `~/.config/ghostty/config` does not exist yet, so there is nothing to back up there.

### 2. Create `~/.config/ghostty/config`
Write this file verbatim (adjust `working-directory` to taste):

```
# ~/.config/ghostty/config
# Read directly by cmux (libghostty). Reload in cmux with Cmd+Shift+, .

# --- Font (JetBrainsMono Nerd Font is installed; glyphs power sidebar/prompt icons) ---
font-family = "JetBrainsMono Nerd Font"
font-size = 13
font-thicken = true

# --- Theme: auto light/dark (catppuccin) ---
theme = dark:catppuccin-mocha,light:catppuccin-latte
window-theme = auto

# --- cmux-optimized window & splits (issue #1657) ---
window-show-tab-bar = never          # cmux provides its own tab UI; hide Ghostty's
unfocused-split-opacity = 0.65       # dim inactive agent panes to clarify focus
window-padding-x = 12                # breathing room next to the cmux sidebar
window-padding-y = 10
window-padding-balance = true
background-opacity = 0.98            # set to 1.0 if you dislike any translucency
# background-blur = true             # optional frosted glass — verify cmux accepts on reload

# --- Terminal behavior ---
working-directory = /Users/bossjones/dev
window-inherit-working-directory = true
copy-on-select = clipboard
clipboard-trim-trailing-spaces = false
mouse-hide-while-typing = true
confirm-close-surface = false        # cmux has its own close guards
scrollback-limit = 10000000
cursor-style = block

# --- macOS ---
macos-option-as-alt = left           # Option word-nav; 'left' avoids non-US keyboard breakage
macos-auto-secure-input = true
macos-titlebar-style = transparent
```

- Rationale per key traces to: tab-bar/opacity/padding/option-as-alt → issue #1657;
  theme pair / copy-on-select / inherit-working-directory → gordonbeeming + subaud.io;
  font-thicken / scrollback / mouse-hide → subaud.io.

### 3. Populate `~/.config/cmux/cmux.json` (curated, explicit)
Uncomment/set the following blocks in the existing JSONC file (keep the `$schema` +
`schemaVersion` header). Everything **not** listed stays commented → falls back to Settings.

```jsonc
"app": {
  "appearance": "system",
  "workspaceInheritWorkingDirectory": true,
  "reorderOnNotification": true,        // surface the agent that just pinged
  "warnBeforeClosingTab": true,
  "openMarkdownInCmuxViewer": true,
  "confirmQuit": "always"
},
"terminal": {
  "autoResumeAgentSessions": true,      // resume agents after reopen — key for CC workflows
  "copyOnSelect": true,                 // mirror the Ghostty copy-on-select choice
  "showScrollBar": true,
  "rendererRealization": { "enabled": true, "idleSeconds": 30, "maxWarmRenderers": 12 }
  // agentHibernation left OFF (default). Enable only if many idle agents strain resources:
  // "agentHibernation": { "enabled": true, "maxLiveTerminals": 12, "idleSeconds": 5 }
},
"sidebar": {
  "watchGitStatus": true,
  "showBranchDirectory": true,
  "showPullRequests": true,
  "makePullRequestsClickable": true,
  "showPorts": true,
  "openPortLinksInCmuxBrowser": true,
  "showProgress": true,
  "branchLayout": "vertical"
},
"automation": {
  "claudeCodeIntegration": true,        // native detection of Claude Code in cmux terminals
  "suppressSubagentNotifications": true // quieter multi-agent runs
  // socketControlMode intentionally omitted → keep default "cmuxOnly".
  // Do NOT change without reading the cmux-socket-policy skill (security surface).
},
"notifications": {
  "paneFlash": true,
  "unreadPaneRing": true,
  "dockBadge": true,
  "sound": "default",
  "hooksMode": "append"
},
"browser": {
  "openTerminalLinksInCmuxBrowser": true,
  "interceptTerminalOpenCommandInCmuxBrowser": true,
  "defaultSearchEngine": "google"
}
```

- Every key above is present in the live cmux.json template, so no schema guessing.

### 4. Claude Code notification bridge — DO NOTHING (it is automatic)

> **RESOLVED by `cmux hooks --help` (probed 2026-07-08, cmux CLI symlinked to `/usr/local/bin/cmux`):**
> *"Claude Code hooks are injected automatically by the cmux Claude wrapper."* Claude Code is
> deliberately **absent** from the `cmux hooks setup` agent list (codex, grok, opencode, pi, omp,
> amp, cursor, gemini, kiro, antigravity, rovodev, hermes-agent, copilot, codebuddy, factory,
> qoder) precisely because the wrapper shim (`CMUX_CLAUDE_WRAPPER_SHIM`, PATH `…/cmux-cli-shims/…`)
> handles it. There is **no `claude` agent to install** and **no `cmux hooks claude install`.**

- **Primary path (recommended, zero-config):** do **not** add anything to `~/.claude/settings.json`
  and do **not** run a `cmux hooks` command for Claude. Keeping `automation.claudeCodeIntegration:
  true` (Step 3) is all that's needed — cmux's wrapper auto-injects the hooks and surfaces
  turn/permission events natively, only ever inside a cmux pane (nothing fires in tmux/plain shell).
  A manual `Stop` hook here would **double-notify**.

- **Optional — only for a *custom* message beyond what the wrapper emits:** `cmux notify` **is
  confirmed to exist**, with this **verified** signature (note: flags are `--title/--subtitle/--body`,
  there is **no `--message`**):
  ```
  cmux notify --title <text> [--subtitle <text>] [--body <text>]
              [--surface <id|ref|index>] [--workspace <id|ref|index>] [--window <id|ref|index>]
  ```
  If you want bespoke text, add a `Stop` hook guarded on `CMUX_SURFACE_ID` and target that surface
  explicitly (`--surface`; explicit surface UUIDs resolve globally per `cmux --help`):
  ```json
  "hooks": {
    "Stop": [
      { "matcher": "", "hooks": [
        { "type": "command", "command": "[ -n \"$CMUX_SURFACE_ID\" ] && cmux notify --surface \"$CMUX_SURFACE_ID\" --title 'Claude Code' --body 'Turn complete' || true" }
      ] }
    ]
  }
  ```
  Guard rationale (CONFIRMED from the earlier `env` probe): cmux exports **no plain `$CMUX`**;
  `CMUX_SURFACE_ID` is always set and non-empty inside a pane, while ⚠️ **`CMUX_SOCKET` is empty**
  (`CMUX_SOCKET=`) — never guard on it. In tmux/plain shell the guard is unset, so `|| true` keeps
  the hook exit-clean. **Because native injection is already active, this custom hook will overlap
  it — disable one path or accept the duplicate.**

- **For your *other* agents (codex, gemini, cursor, opencode, …):** those are NOT auto-wired. Run
  `cmux hooks setup` (all agents on PATH) or `cmux hooks <agent> install` per agent to get the same
  notification bridge. Out of scope for this Claude-focused spec, but noted since you run multi-agent.

- **Document the outcome:** record that Claude Code uses the automatic wrapper path (no manual
  hook), or — if you opt into the custom hook — that it targets `--surface "$CMUX_SURFACE_ID"` and
  how you resolved the overlap with native injection.

### 5. Remove the dead stub
- Delete `~/.config/ghostty/config.ghostty` (0 bytes, read by nothing).

### 6. Reload and validate (see Validation Commands)
- Run `cmux config doctor` to confirm `cmux.json` JSONC is valid, then `cmux reload-config`
  (reloads **both** the Ghostty config and `cmux.json` and refreshes terminals in place — no app
  restart). Confirm no ignored/rejected keys, and visually confirm font, theme, tab-bar-off, split
  dimming, and the git/PR/ports sidebar.

## Testing Strategy

This is configuration, not code, so "tests" = observable behavior after reload:

- **Ghostty parse check:** after reload, cmux must not report unknown-key warnings. The
  `# verify`-flagged keys (`background-blur`, and `background-opacity` translucency) are the only
  ones that might be rejected/unsupported — if so, comment them out and re-reload.
- **JSONC validity:** run `cmux config doctor` — it reports `JSONC syntax is valid` and lists the
  parsed top-level keys. A malformed file makes cmux fall back silently, so confirm doctor lists the
  namespaces you added (not just `$schema, schemaVersion`) rather than assuming they took effect.
- **Font glyphs:** a Nerd Font glyph (e.g. a git branch icon in the sidebar) renders, proving
  `font-family` resolved to the installed JetBrainsMono Nerd Font.
- **Theme toggle:** switching macOS light/dark flips cmux between mocha and latte.
- **Split dimming:** with two panes, the unfocused one is visibly dimmer (0.65 opacity).
- **Notification bridge:** trigger a Claude Code `Stop` from inside cmux and confirm the pane
  flashes / Dock badges via native integration. Only if the Step 4 Option 1 hook is added: confirm
  it doesn't double-notify inside cmux, and that a `Stop` from tmux/plain shell short-circuits
  cleanly on the empty `CMUX_SURFACE_ID` guard (no `cmux notify` error, no stall).
- **Rollback path:** `cp ~/.config/cmux/cmux.json.bak ~/.config/cmux/cmux.json` restores the
  prior state if anything regresses.

## Acceptance Criteria

- `~/.config/ghostty/config` exists and contains the JetBrainsMono + catppuccin + cmux-optimized
  block; cmux reloads it with zero unknown-key warnings (flagged keys either accepted or removed).
- `~/.config/cmux/cmux.json` has the six populated namespaces above (no longer all-commented) and
  still parses; `automation.socketControlMode` remains at its default.
- Ghostty's own tab bar is hidden; unfocused splits are dimmed; sidebar shows git branch, PR, and
  ports.
- A Claude Code turn inside cmux produces a native notification via the **automatic** wrapper
  injection — with **no** manual `~/.claude/settings.json` hook added. If the optional custom-message
  hook is nonetheless used, it targets `--surface "$CMUX_SURFACE_ID"`, does not duplicate the native
  ping inside cmux, and exits clean (no error/stall) when a `Stop` fires in tmux/plain shell.
- `cmux config doctor` reports valid JSONC and `cmux reload-config` applies both files with no
  ignored/rejected keys.
- `~/.config/ghostty/config.ghostty` no longer exists.
- `~/.config/cmux/cmux.json.bak` exists as a rollback point.

## Validation Commands
Execute these to validate the task is complete:

- `ls -l ~/.config/ghostty/config` — new config exists (non-zero size).
- `ls ~/.config/ghostty/config.ghostty 2>&1` — should report "No such file" (stub removed).
- `cmux config doctor` — **authoritative** JSONC validation (replaces any hand-rolled JSON parse);
  prints `JSONC syntax is valid` and lists the top-level keys it parsed. `cmux config paths` prints
  the config + schema URLs.
- `cmux reload-config` — reload Ghostty config + `cmux.json` and refresh terminals in place; then
  visually confirm font, catppuccin theme, no Ghostty tab bar, dimmed unfocused split, and the
  populated git/PR/ports sidebar. No app restart needed.
- Claude Code bridge: no verb probe needed — `cmux notify` is confirmed to exist. Trigger a `Stop`
  inside cmux and confirm the pane flashes via the **automatic** wrapper injection (no manual hook).
- Only if you added the optional custom hook (Step 4): confirm it doesn't **duplicate** the native
  ping inside cmux, and that a `Stop` from tmux/plain shell exits clean on the empty
  `CMUX_SURFACE_ID` guard (no `cmux notify` error, no stall).
- `ls -l ~/.config/cmux/cmux.json.*.bak` — timestamped rollback backup present.

## Notes

- **Authoritative key source:** the live `~/.config/cmux/cmux.json` template is the source of
  truth for cmux keys — the fetched docs page listed a few keys (e.g. `globalFontMagnification`,
  `rightMaxWidth`, `shortcuts.when`) that are **not** in the template, so this spec deliberately
  avoids them.
- **cmux reads Ghostty config, not a cmux-specific terminal file** — confirmed by cmux's own agent
  guidance (`cmux --help`): *"prefer Ghostty config for terminal behavior Ghostty already
  supports … Ghostty config lives at `~/.config/ghostty/config` (controls terminal transparency,
  blur, font, theme, keybinds)."* So `background-opacity`/`background-blur`/font/theme correctly
  belong in the Ghostty file; `cmux.json` governs the cmux app shell (sidebar, browser,
  notifications, automation, shortcuts).
- **cmux CLI is the source of truth** (now symlinked to `/usr/local/bin/cmux`): validate with
  `cmux config doctor`, discover paths with `cmux config paths`, read settings docs with
  `cmux docs settings`, reload with `cmux reload-config`. Optional font tweaks without editing JSON:
  `cmux config set sidebar-font-size <10-20>` and `cmux config set surface-tab-bar-font-size <8-24>`.
- **Other agents (out of scope but noted):** `cmux hooks setup` (or `cmux hooks <agent> install`)
  wires the same notification bridge for codex/gemini/cursor/opencode/etc.; Claude Code needs none
  of this (auto-injected).
- **Security:** `automation.socketControlMode` stays `"cmuxOnly"`. The `cmux` control skill and
  CLI automation may want a broader mode, but that widens the socket attack surface — treat it as
  a separate, deliberate change gated by the `cmux-socket-policy` skill.
- **No new libraries.** JetBrainsMono Nerd Font is already installed; if the user later prefers
  Monaspace/MonoLisa, install via `brew install --cask font-monaspace` (or MonoLisa manually) and
  swap `font-family`.
- **Font/theme were user-selected** during planning: JetBrainsMono Nerd Font + catppuccin
  mocha/latte. Scope selected: core settings + Claude Code integration.
