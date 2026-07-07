---
description: Kick off tutorial / documentation generation by delegating to `/documentation-generation:doc-generate`, routing the work to the correct fully-qualified tutorial-engineer subagent (documentation-generation for docs, code-documentation for code). Defaults to a tutorial on the current branch's features; asks clarifying questions before writing.
argument-hint: "[what to document — defaults to a tutorial on the current branch's features]"
---

# Docs Tutorial

## Purpose

You are an orchestrator that produces a tutorial (or other documentation) by delegating to the
`/documentation-generation:doc-generate` command, told explicitly which **fully-qualified**
tutorial-engineer subagent to implement with. The whole reason this command exists is that the
subagent name is easy to misremember — so this command pins the two correct names and routes
between them by the nature of the request. It never writes the doc itself; it resolves the topic,
picks the subagent, clears up ambiguity with the user, then hands the work to `doc-generate`.

## Variables

PROMPT: $ARGUMENTS # what to document. If empty, default to "a tutorial about the features
                   # introduced on the current git branch".

## The two subagents (spelled out so they can't be misremembered)

- **Documentation-related** work (writing/updating tutorials, guides, references, onboarding docs):
  `documentation-generation:documentation-generation-tutorial-engineer`
- **Code-related** work (generating or annotating code, docstrings, inline code walkthroughs):
  `code-documentation:code-documentation-tutorial-engineer`

Both are "tutorial-engineer" variants; the only difference is which plugin owns them. Default to the
`documentation-generation` variant for prose docs, since it pairs with
`/documentation-generation:doc-generate`.

## Instructions

1. **Resolve the topic.** If `PROMPT` is non-empty, use it verbatim. If it is empty, default to a
   tutorial about the features on the **current branch** — determine the branch and its changes:

   ```bash
   git rev-parse --abbrev-ref HEAD
   git diff --stat main...HEAD
   ```

   Summarize what the branch adds and use that as the tutorial topic.

2. **Classify the request → pick the subagent.** Decide whether the work is documentation-related
   or code-related and select the matching fully-qualified name from the section above. If the
   prompt makes this ambiguous, **ask the user** which they want rather than guessing.

3. **Ask clarifying questions before working.** Do NOT start writing until these are settled:
   - **Search for existing material first.** Look under `plugins/**/docs/` and the repo's `docs/`
     for pages already covering this subject, and surface what you found.
   - **New doc vs. update existing.** If a doc on the same subject already exists, ask whether to
     write a new page or update the existing one — and whether to update its cross-references
     (TOC entries, summary tables, README links, sibling `docs/*.md` sections).
   - **Scope.** Confirm the scope (e.g. one combined tutorial vs. separate tutorials). Use your
     judgement to propose a default, but let the user override.
   - Skip a question only when the prompt already answers it unambiguously.

4. **Delegate to `doc-generate`.** Invoke `/documentation-generation:doc-generate` with an explicit
   instruction line naming the chosen subagent, the resolved topic, the target file path(s), and the
   new-vs-update decision. For example:

   ```text
   /documentation-generation:doc-generate Implement using the
   `documentation-generation:documentation-generation-tutorial-engineer` subagent. Write a new
   tutorial at <path> covering <topic>. Source material: <files>. <new|update> — update the
   cross-references in <files> when done.
   ```

## Workflow

1. **Resolve** the topic from `PROMPT` (or the current-branch default).
2. **Classify** the request and pick the fully-qualified subagent; ask the user if ambiguous.
3. **Clarify** with the user: existing material found, new-vs-update, and scope.
4. **Delegate** to `/documentation-generation:doc-generate` with the subagent name, topic, target
   path, sources, and new-vs-update decision spelled out.
5. Now follow the `Report` section.

## Report

```
## Docs tutorial — dispatched

**Topic**: [resolved topic]
**Subagent**: [documentation-generation:documentation-generation-tutorial-engineer | code-documentation:code-documentation-tutorial-engineer]
**Target**: [path(s) written or updated]
**Mode**: [new doc | update existing]
**Cross-references updated**: [files, or "none"]
```
