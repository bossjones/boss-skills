# Database branching for worktrees

Load this only when the worktree's work touches the schema or data model and
the project uses a branchable database. For a bug fix with no schema change,
skip it — share the existing database.

## When to create a database branch

| Scenario                   | Branch the DB? |
| -------------------------- | -------------- |
| Schema migrations          | Yes            |
| Data-model refactoring     | Yes            |
| Performance experiments    | Yes            |
| Bug fix (no schema change) | No             |

Create the branch **before** running migrations so each worktree gets an
isolated database.

## Provider quick reference

| Provider           | Create branch                                            | Clean up                                          |
| ------------------ | -------------------------------------------------------- | ------------------------------------------------- |
| **Neon**           | `neonctl branches create --name <branch> --parent main`  | `neonctl branches delete <branch>`                |
| **PlanetScale**    | `pscale branch create <db> <branch>`                     | `pscale branch delete <db> <branch>`              |
| **Local Postgres** | `psql -c "CREATE SCHEMA <schema>;"`                      | `psql -c "DROP SCHEMA <schema> CASCADE;"`         |

After creating a branch, update the worktree's `DATABASE_URL` (in its copied
`.env`) to point at the new branch. Do not print the file — edit it in place.

`/git-worktree-remove` and `/git-worktree-clean` print the matching cleanup
command as a reminder; the database branch is never deleted automatically.
