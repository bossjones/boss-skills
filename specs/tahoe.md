# Spec: macOS Sequoia → Tahoe Upgrade Runbook

## Task Description

An audit of this machine (MacBook Pro, Apple M4 Max, macOS Sequoia 15.7.7) plus current
(mid-2026) research into macOS Tahoe (macOS 26) compatibility, to answer: *"are there any
problems I should know about before moving to Tahoe?"* This document is the answer — a
machine-specific risk register and step-by-step upgrade runbook, not generic advice.

## Objective

Give a clear go/no-go verdict, a ranked list of what could actually break on *this* machine,
and an executable checklist covering pre-upgrade prep, upgrade day, and post-upgrade
validation, so the upgrade can be done with no surprises.

## Verdict

**Green light. Low overall risk — with 4 must-dos before you upgrade.**

This is about as clean a Tahoe upgrade candidate as exists: fully-supported Apple Silicon
hardware with headroom to spare, zero third-party kernel/system extensions, no MDM, and a
lean dev toolchain. The real risk here isn't the OS — it's three specific pieces of software
(Xcode CLT, VMware Fusion, and the absence of a backup) plus picking the right point release.

**The 4 must-dos, in priority order:**

1. **Back up first.** No Time Machine backup currently exists on this machine (see
   [Gap Found](#gap-found) below). Configure and *verify* a completed backup before touching
   the installer.
2. **Update VMware Fusion before the OS**, not after. Fusion 25.0.1 is behind the
   Tahoe-compatible line.
3. **Target macOS 26.4.1 or the 26.5 line** — skip 26.0, 26.1, and 26.3, which have
   documented, dev-impacting bugs.
4. **Reinstall Xcode Command Line Tools immediately after upgrading.** This is the
   single most likely thing to break, and it cascades into Homebrew and pyenv.

## Audited System Snapshot

Gathered directly from this machine (read-only commands: `sw_vers`, `system_profiler`,
`sysctl`, `brew`, `pyenv`, `systemextensionsctl`, `kextstat`, `csrutil`, `fdesetup`,
`profiles`, `tmutil`, `defaults read`).

| Category | Finding |
|---|---|
| Model | MacBook Pro, **Mac16,5** |
| Chip | **Apple M4 Max** (16 cores: 12P + 4E), arm64 |
| Memory | **128 GB** |
| Current OS | **macOS 15.7.7**, build 24G720 |
| Disk | 3.6 TB total, **1.9 TB free** (1% used on data volume) |
| FileVault | On |
| SIP | Enabled |
| MDM / DEP | Not enrolled |
| Rosetta 2 | Installed and active |
| System extensions | **0** |
| Third-party kexts | **0** |
| `/Library/QuickLook` plugins | Empty |
| Xcode CLT | **26.1.0** (already the Tahoe-era toolchain, installed while on Sequoia) |
| Swift | 6.2.1 |
| Homebrew | 6.0.9 at `/opt/homebrew` (arm64) — 343 formulae, 25 casks, **143 outdated**, 11 third-party taps |
| pyenv | 2.6.6 — only **Python 3.12.8** + one `yt-dlp3` virtualenv |
| Other toolchains | uv 0.11.14, node v22.14.0 (fnm), rbenv 1.3.2, Homebrew go, rustc/cargo 1.96.0 |
| Shell / terminal | Homebrew zsh; **iTerm2** inside **tmux** |
| Casks of note | **VMware Fusion 25.0.1**, **Docker Desktop 4.81.0** (engine 29.6.1), IINA 1.4.2, Calibre, 1Password CLI, qlvideo, quicklook-video; remaining casks are fonts |
| Login items | Perplexity Comet + Google (Keystone) updater agents only — nothing system-invasive |

### Gap Found

`tmutil latestbackup` returned nothing — **no Time Machine backup is configured on this
machine.** This is unrelated to Tahoe specifically but is the single highest-impact risk for
*any* major OS upgrade and must be closed first.

## Risk Register

Ranked by how likely each is to actually bite this specific machine, based on its installed
versions and current (mid-2026, Tahoe on the 26.4.x/26.5 line) field reports.

| # | Risk | Why it applies to you | Action | Severity |
|---|---|---|---|---|
| 1 | **Xcode CLT gets invalidated/relocated by the upgrade**, breaking Homebrew and pyenv | You have CLT 26.1 installed *on Sequoia*; the OS upgrade process routinely strips or relocates CLT and Homebrew's `/opt/homebrew` symlinks into "Relocated Items." CLT 26.1 is also separately reported to fail installing *on* Tahoe 26.1 | Run `xcode-select --install` right after upgrading; target OS 26.2+ so a clean CLT install succeeds; verify `xcrun --show-sdk-path` resolves before running `brew` or `pyenv` commands | High (probability) |
| 2 | **VMware Fusion 25.0.1 is behind the Tahoe-compatible line** | You run Fusion for VMs | Update Fusion to **25H2u1 or 26H1+** and VMware Tools to **13.1.0+** *before* upgrading macOS — do this on Sequoia first. Known-good pairing: Tahoe 26.5 ↔ Fusion 26H1 | Medium–High |
| 3 | **Landing on a bad Tahoe point release** | You're choosing what to install | Skip **26.0/26.1** (CLT install bug) and **26.3** (widely-reported crash-loop bug on Apple Silicon). Target **26.4.1** or the **26.5** line, considered the current stable daily-driver point | Medium |
| 4 | **Docker's Rosetta-based x86/amd64 emulation regressed on Tahoe** | Docker Desktop 4.81.0 installed; relevant only if you run amd64 Linux containers | The "Use Rosetta for x86/amd64 emulation" setting has a documented AVX bug (assertion failure in `ThreadContextSignals.cpp`; SQL Server 2025 containers are the clearest reproduction). If you hit it: toggle Rosetta emulation off (falls back to QEMU) or evaluate OrbStack, which handles this better on Tahoe | Medium (conditional) |
| 5 | **No backup exists** | Confirmed via `tmutil latestbackup` | Configure Time Machine (or a full clone) and confirm a completed backup before the upgrade | High (impact) |
| 6 | **Homebrew post-upgrade housekeeping** | 143 packages already outdated pre-upgrade | Homebrew is Tier-1 supported on Tahoe; existing bottles keep working. After upgrading: `brew update && brew doctor && brew upgrade` to pull native `arm64_tahoe` bottles. If `/opt/homebrew` got relocated by the installer, restore the symlinks | Low |
| 7 | **pyenv-built Pythons after the OS jump** | Only Python 3.12.8 + one venv — small footprint | Existing builds keep working once CLT is fixed. If you build a *new* Python version on Tahoe and it fails `configure`/SSL, pass `CONFIGURE_OPTS="--with-openssl=$(brew --prefix openssl)"` and point `LDFLAGS`/`CPPFLAGS` at `$(brew --prefix readline)` | Low |
| 8 | **Rosetta 2 long-term deprecation** | You rely on Rosetta for x86 tooling | Tahoe fully supports Rosetta 2 today. Starting in **26.4+**, launching a Rosetta-dependent app shows a deprecation warning. macOS 27 (fall 2026) still ships Rosetta. **macOS 28 (fall 2027)** removes it broadly, keeping it only for a narrow set of legacy games and x86-in-Linux-VM cases. Not a Tahoe blocker — but start migrating x86 CLI tooling to arm64-native over the next ~18 months | Low (now) |
| 9 | **App-level bugs/cosmetics** | iTerm2, IINA, 1Password, Calibre, qlvideo all installed | Update each after upgrading. Notables: iTerm2 has shipped Tahoe/Liquid-Glass fixes (tab-label truncation, stoplight buttons); IINA had subtitle-display and crash bugs on early Tahoe (26.0.1) — use latest; 1Password's Apple Watch unlock broke after 26.4 (documented workaround exists); Calibre's wireless eReader connections can fail under Tahoe's local-network permission model; **qlvideo v3 requires Tahoe and switches to Media Extensions/AVFoundation — legacy `.qlgenerator` plugins are dead, reinstall the v3 build** | Low |

## Pre-Upgrade Checklist

Do these **on Sequoia**, before running the Tahoe installer:

1. **Back up.**
   - Enable Time Machine to an external disk or network target, or make a full clone (e.g.
     Carbon Copy Cloner / SuperDuper).
   - Verify: `tmutil latestbackup` returns a completed snapshot.
2. **Update VMware Fusion and VMware Tools** to the latest Tahoe-compatible build
   (25H2u1/26H1+, Tools 13.1.0+). Do this *before* the OS upgrade — do not restore or resume
   VMs on the old Fusion build post-upgrade.
3. **Update Homebrew and packages** while still on a known-good OS: `brew update && brew
   upgrade` (clears part of the 143-outdated backlog and reduces post-upgrade noise).
4. **Confirm current app versions** you'll want to re-check post-upgrade: Docker Desktop
   4.81.0, IINA 1.4.2, 1Password CLI, Calibre, qlvideo/quicklook-video.
5. **Choose the installer**: download **macOS Tahoe 26.4.1** or the current **26.5** point
   release specifically — do not install 26.0, 26.1, or 26.3.
6. Ensure the Mac is on Sequoia's latest available update before jumping (reduces delta risk).

## Upgrade Day

1. Confirm the verified backup from step 1 above is complete and restorable.
2. Quit VMware Fusion and Docker Desktop before starting the installer.
3. Install macOS Tahoe 26.4.1 (or 26.5).
4. On first boot, do **not** immediately resume VMware Fusion VMs — open Fusion first and
   confirm it reports itself as up to date for the new OS.
5. Let Spotlight/system indexing settle before judging performance.

## Post-Upgrade Validation

Run in order:

```bash
# 1. Confirm OS version
sw_vers                                    # expect ProductVersion 26.4.1 or 26.5.x

# 2. Reinstall Command Line Tools (the linchpin step — do this before anything else)
xcode-select --install
xcrun --show-sdk-path                      # should resolve cleanly, no errors

# 3. Homebrew sanity + upgrade to native Tahoe bottles
brew update && brew doctor && brew config  # brew config should report macOS 26.x
brew upgrade

# 4. pyenv / Python sanity
pyenv versions
python -c 'import ssl; print(ssl.OPENSSL_VERSION)'   # confirms SSL still links correctly

# 5. Docker sanity
docker run --rm hello-world
# If you run amd64/x86_64 images, test one explicitly and watch for Rosetta/AVX failures

# 6. VMware Fusion
# Open Fusion, confirm version banner, then boot one VM to confirm it starts cleanly
```

Then update the remaining apps to their latest Tahoe builds: iTerm2, IINA, 1Password,
Docker Desktop, qlvideo (must move to the v3/Media Extensions build), Calibre (re-grant
local-network permission if wireless eReader sync stops working).

## Rosetta 2 Sunset Note

Not an immediate blocker, but worth planning around since this machine actively uses Rosetta
for x86 tooling:

- **Tahoe (26.x):** Rosetta 2 fully supported. From 26.4 onward, macOS shows a warning dialog
  when launching a Rosetta-dependent app, flagging that it won't work forever.
- **macOS 27 (expected fall 2026):** Apple Silicon only, but Rosetta 2 still included.
- **macOS 28 (expected fall 2027):** Rosetta 2 broadly removed, retained only for a narrow
  set of legacy games and x86 binaries inside Linux VMs.

Practical takeaway: use the Tahoe→macOS 27 window to identify and migrate any x86-only CLI
tools, Homebrew formulae, or Docker images you depend on to arm64-native equivalents before
macOS 28 ships.

## Acceptance Criteria

- Backup verified complete before the Tahoe installer runs.
- VMware Fusion + Tools updated to a Tahoe-compatible build before the OS upgrade.
- Installed OS is 26.4.1 or later in the 26.x line (not 26.0/26.1/26.3).
- Post-upgrade validation commands all succeed with no unresolved errors, in particular
  `xcrun --show-sdk-path` and `brew doctor`.
- VMware Fusion VMs boot successfully post-upgrade.
- Docker Desktop runs `hello-world`; any amd64 workloads tested explicitly if used.

## Validation Commands

Execute these to confirm this document itself is in place and well-formed:

- `test -f specs/tahoe.md && wc -l specs/tahoe.md` — confirm the file exists
- `make markdown-lint` — repo markdown lint (if configured to cover `specs/`)

## Notes

- This is an advisory/runbook document only — no code or dependency changes are implied by
  writing it.
- Research reflects the state of macOS Tahoe as of mid-2026 (Tahoe on the 26.4.x/26.5 line).
  Re-check point-release stability if the actual upgrade happens much later than this audit.
- Sources consulted during research include Homebrew's official support-tier docs, Apple
  Developer Forums, Broadcom/VMware community threads and the official Fusion guest-OS
  compatibility guide, the pyenv GitHub issue tracker, iTerm2's release notes, and multiple
  2026 community/press reports on Tahoe point-release stability (MacRumors, AppleInsider,
  TechTimes, Eclectic Light).
