# Lens: placement

`theme: "placement"`. Where files live, what they are named, and whether that matches a
discoverable convention.

Run every gate in `quality-gates.md`. Return only the JSON in `observation-format.md`.

**This lens is strictly rules-driven.** Unlike the other lenses, it has no built-in opinion about
where a file belongs — that would mean inventing a convention for a repo this skill has never
seen, which is worse than saying nothing. Report only what you can cite to a discovered rule
(Step 2 / `references/repo-profile.md`) or a demonstrable convention in the sibling files
("every other file in this directory is kebab-case, this one is not"). **With no governing rule
or demonstrable pattern, report nothing.** A quiet placement lens in an unfamiliar repo is
correct, not a failure.

## Domain

New, moved, renamed, and deleted files. Directory choice, nesting depth, filename shape.

**Not yours:** whether the index was updated (`cross-refs`), what the file *says*
(`claims` / `consistency`).

## What to check

**Discovered folder rules.** If `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/`, or a nested
`README.md` states an explicit rule about where a certain kind of file belongs, cite it by path
and enforce it. Do not paraphrase a rule you are not looking at.

**Demonstrable sibling convention.** Look at every other file in the same directory. If they are
uniformly named a certain way (kebab-case, a date prefix, a numbered prefix) and the new file
breaks that pattern with no rule saying otherwise, that is still a finding — it is evidence, not
invention, because the pattern is observable in the diff's own neighbourhood. State how many
sibling files you checked.

**Two universal checks that need no discovered rule:**

- **A committed file that `.gitignore` excludes.** If a tracked file's path matches a pattern in
  `.gitignore`, it had to be force-added (`git add -f`) to get there. That is worth flagging
  regardless of any other convention — it is evidence the file was not meant to be tracked.
- **A filename shape inconsistent with every sibling**, as above.

**Naming, when a convention exists.** Casing (kebab-case, snake_case) and date format
(`YYYY-MM-DD` vs. relative), if the discovered rules or the sibling files establish one.

## Priority

MEDIUM for a wrong folder or a wrong filename shape that breaks discovery, when a rule or a
sibling pattern actually supports the claim. HIGH for a force-added, gitignored file — that is a
hygiene problem, not a tidiness one. LOW for nesting depth, when the repo has an opinion on it at
all.

## Categories

`wrong-folder`, `wrong-filename`, `nesting-depth`, `invented-subfolder`, `gitignored-but-tracked`,
`folder-contract-inverted`.

## Evidence bar

The path as added, either the rule quoted by path or the sibling-file pattern with a count, and
the path it should have taken. Never assert a placement rule you cannot point to.

## Do not report

A file the diff did not add or move. Preference about a folder name with no rule or sibling
pattern behind it. Anything a discovered pre-commit hook, CI check, or linter already enforces
(quality gate 8). Nesting depth in a repo with no stated or demonstrable opinion on it.
