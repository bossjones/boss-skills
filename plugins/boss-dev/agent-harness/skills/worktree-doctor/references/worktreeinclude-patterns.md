# `.worktreeinclude` candidate patterns

`worktree-doctor` scans a repo's **gitignored** files and flags those that
usually need to follow the repo into each worktree. Only files that are both
gitignored and matched here are real candidates — tracked files are already
present in a new worktree.

## Default candidate patterns

| Pattern               | Why it should follow a worktree                          |
| --------------------- | -------------------------------------------------------- |
| `.env`                | Base environment variables (DB URLs, API hosts)          |
| `.env.*`              | Environment-specific overrides (`.env.local`, `.env.dev`)|
| `.envrc`              | direnv config — protected; copy triggers `direnv allow`  |
| `*.local`             | Local-only config (e.g. `config.local`)                  |
| `*.local.json`        | Local-only JSON config                                   |
| `settings.local.json` | Editor / Claude local settings                           |
| `secrets`, `secrets.*`, `secrets/*` | Local secret files a worktree still needs  |

## Excluded paths

Vendored and build output is never a candidate, even if it matches a pattern:
`.git`, `.venv`/`venv`, `node_modules`, `site-packages`, `dist`, `build`,
`target`, `__pycache__`, and the various cache dirs. These are regenerated per
worktree, not copied.

## Secrets caution

`.env` and `.envrc` hold secrets. They are copied byte-for-byte by the
`git-worktree` script and must never be printed, `cat`-ed, or logged. `.envrc`
is a Claude protected path, so its copy may prompt under `default`/`acceptEdits`.

## Tuning

If the doctor misses a project-specific file, add it to `.worktreeinclude` by
hand (gitignore glob syntax). If it suggests something you do not want copied,
omit that line — the file stays out of new worktrees.
