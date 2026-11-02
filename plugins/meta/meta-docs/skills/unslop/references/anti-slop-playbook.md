# Anti-Slop Playbook

This playbook synthesizes the operational patterns for anti-slop skills from
[Flavio Copes' anti-slop guide](https://flaviocopes.com/anti-slop/) and
[unslop walkthrough](https://flaviocopes.com/unslop/), adapted for the `meta-docs` plugin.

## 1. Why anti-slop runs as a separate review pass

When an AI agent drafts an article, README, specification, or pull request description, it juggles
the prompt, the source code, the repository conventions, and the target structure. Adding a final
line such as "do not sound like AI" competes for attention with completing the draft.

Run anti-slop as a **separate pass** after the draft is complete:

1. **Draft first**: Give the agent the facts, sources, commands, and goal to produce the complete
   initial version.
2. **Review second**: Invoke `unslop` (or delegate to the `docs-anti-slop-reviewer` subagent) with a
   focused review prompt:

   ```text
   Review the finished documentation using the unslop skill.

   Keep the facts, commands, examples, and intended structure.
   Fix only the patterns covered by the skill.
   Show me the resulting changes.
   ```

3. **Inspect the diff**: Treat every anti-slop edit as a proposal. Verify that the pass did not
   remove a deliberate turn of phrase, flatten intentional short-paragraph rhythm, or alter a
   technical constraint.

## 2. Choosing the right `meta-docs` skill

| Skill | Primary target | Best for | Key mechanism |
|---|---|---|---|
| `unslop` | Technical prose, READMEs, PR bodies, commit messages, release notes | Fast, deterministic cleanup of common AI writing habits in English technical docs | 28 numbered rules with stable IDs (including Rule 27's "other project's docs" test and Rule 33's anti-telegraphic rule) |
| `humanize-skills` | Multi-language prose, long documents (`1,500+` words), domain-specific writing | Rewriting or auditing across 20 languages, 10 modes (`--technical`, `--academic`, `--legal`, etc.), and voice calibration (`--calibrate`) | Pre-flight 0-100 scoring with a **no-edit gate**, fact-lock intake ledger, surface + structural passes, and side-by-side `*.humanized.*` output for long files |
| `interrogate` | Documentation contracts, specifications, architecture plans, code diffs | Proving whether documented commands, flags, file paths, and claims actually hold up | Parallel adversarial subagents that must prove every finding with an executable command or check |

## 3. Customizing anti-slop rules for your project

A generic anti-slop checklist is a starting point. When you notice a generic rule flattening your
team's teaching style, or missing a recurring project habit, pass project-specific overrides in the
prompt or in your repo's `CLAUDE.md` / `AGENTS.md`:

### Example: Tutorial and blog override block

```markdown
## Project anti-slop overrides

- Open with the useful point or concrete command. Delete generic introductions.
- Keep paragraphs short and explain one idea at a time.
- Replace broad claims with facts, commands, or real examples.
- Introduce code blocks with one sentence before showing them.
- Remove sections that repeat an earlier point.
- Preserve first-person observations and deliberately short one-sentence paragraphs.
```

## 4. Worked before-and-after example (`portwho`)

### Before (`draft.md`)

```markdown
# 🚀 portwho: Your Ultimate Port Detective

In today's fast-paced development landscape, port conflicts can be a frustrating roadblock —
disrupting your workflow and slowing down your entire team. portwho serves as a powerful,
lightweight, and intuitive command-line tool that seamlessly identifies which process is using a
given port.

It's not just a port checker — it's a comprehensive solution for modern developers. Whether you're
debugging a stubborn dev server, juggling microservices, or simply exploring your system, portwho
empowers you to take full control of your environment.

**Key Features:**

- **Instant Detection:** Run `portwho 3000` to instantly see the PID, the process name, and the
  user, ensuring a smooth development experience.
- **Cross-Platform Support:** Works seamlessly on macOS and Linux, fostering consistency across
  your team.
- **Developer-Friendly Output:** Clean, readable output that showcases exactly the information you
  need.

Experts agree that efficient tooling is crucial for developer productivity. With portwho, the
future of port management looks bright.
```

### Rules triggered

- **Rule 18 (Decorative emojis)** & **Rule 17 (Title case headings)**:
  `# 🚀 portwho: Your Ultimate Port Detective`
- **Rule 7 (AI vocabulary)**: `landscape`, `fostering`, `showcases`, `crucial`
- **Rule 13 (Em dash overuse)**: `roadblock — disrupting`, `checker — it's`
- **Rule 8 (Fancy ways to say "is")**: `serves as`
- **Rule 9 ("Not just X, but Y")**: `It's not just a port checker — it's a comprehensive solution`
- **Rule 10 (Rule of three)** & **Rule 27 (Say what it does, not how it feels)**:
  `powerful, lightweight, and intuitive`, `empowers you to take full control`
- **Rule 16 (Inline-header lists)** & **Rule 3 (Superficial `-ing` phrases)**:
  `**Instant Detection:** ... ensuring a smooth development experience.`
- **Rule 5 (Vague attributions)** & **Rule 25 (Generic conclusions)**: `Experts agree...`,
  `the future of port management looks bright.`

### After (`unslop` pass)

```markdown
# portwho

`portwho` is a command-line tool for macOS and Linux that shows which process is listening on a
port.

Run `portwho 3000` to print the PID, process name, and user for port 3000.
```

Every factual detail (`portwho 3000`, `PID`, `process name`, `user`, `macOS and Linux`) survives;
every sentence that could have appeared unchanged in another project's README is gone.

## 5. What anti-slop skills cannot do

An anti-slop skill cleans up repetitive writing habits, but it cannot supply missing facts, choose
the right architecture, or verify that a documented command actually works. Never use prose cleanup
as a substitute for technical verification—pair `unslop` or `humanize-skills` with `interrogate`
when reviewing specs, tutorials, or pull requests.
