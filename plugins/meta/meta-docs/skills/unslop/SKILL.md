---
name: unslop
license: MIT
description: >-
  Cut AI writing tells, filler phrases, chatbot residue, and formulaic punctuation from
  documentation, READMEs, pull request descriptions, commit messages, and prose. Applies 28
  numbered detection rules while preserving technical facts, commands, and intended tone. Use
  when asked to unslop, de-slop, tighten prose, remove AI tells, or run a separate anti-slop
  review pass on drafted text.
---

# Unslop

Edit text to remove AI writing patterns. Scan for the 28 numbered patterns below, then rewrite while
preserving technical facts, commands, examples, and intended tone.

For guidance on running `unslop` as a separate review pass, customizing rules for your project, and
comparing `unslop` against `humanize-skills` and `interrogate`, see
[references/anti-slop-playbook.md](references/anti-slop-playbook.md).

## Separate review pass workflow

When an agent drafts a document, README, tutorial, or pull request description, its primary job is
finishing the content accurately. Appending "do not sound like AI" to a drafting prompt competes
with content generation. Run `unslop` as a dedicated second pass instead:

1. **Preserve facts, commands, and structure**: Keep every CLI command, code block, file path,
   flag, URL, metric, and architectural claim unchanged. Never invent facts or delete required
   technical caveats to make a sentence shorter.
2. **Respect local project voice**: If the user or repository specifies project-specific style
   overrides (for example, keeping intentional one-line paragraphs in a tutorial or preserving a
   required heading casing convention), apply the local override first.
3. **Fix only the patterns below**: Do not rewrite clean human sentences just to appear thorough.
4. **Present changes as an inspectable proposal**: When editing a file or passage interactively,
   make the diff easy to inspect (or summarize the rule numbers triggered) so the author can accept
   or revert individual adjustments.

## Patterns to detect and fix

<!-- markdownlint-disable MD029 -->

Rule numbers are stable IDs that other skills and review passes cite. A removed rule leaves a gap
(`1, 2, 4, 6, 21` are intentionally retired).

### Content

3. **Superficial `-ing` phrases.** "highlighting...", "ensuring...", "reflecting...",
   "showcasing...", "fostering...". Delete or expand with real sources.
5. **Vague attributions.** "Experts believe", "Industry reports suggest", "Some critics argue". Name
   the source or delete.

### Language

7. **AI vocabulary.** Additionally, crucial, delve, enduring, enhance, fostering, garner, interplay,
   intricate, landscape (abstract), pivotal, showcase, tapestry (abstract), testament, underscore,
   vibrant. Replace with plain words.
8. **Fancy ways to say "is".** "serves as", "stands as", "boasts", "features". Say "is" or "has".
9. **"Not just X, but Y."** State the point directly instead.
10. **Rule of three.** Don't force ideas into groups of three. Use the natural number.
11. **Synonym cycling.** Protagonist, main character, central figure, hero all in one paragraph.
    Pick one, repeat it.
12. **False ranges.** "from X to Y" where X and Y aren't on a meaningful scale. List topics
    directly.

### Style

13. **Em dash overuse.** Avoid em dashes entirely. Use periods or commas only (no parentheses, no en
    dashes, no hyphen-as-dash substitutes). If a thought needs separation, end the sentence or use a
    comma.
14. **Colon overuse.** Colons are fine before a list or example, not as mid-sentence connectors. "If
    you're coming from traditional automation: instead of registering event handlers, you describe
    conditions" adds nothing with the colon. Rewrite to let the point stand on its own without
    crutch punctuation: "Describe the conditions under which the scheduler should fire instead of
    registering event handlers." Same meaning, no mid-sentence colon.
15. **Boldface overuse.** Don't bold every proper noun or acronym.
16. **Inline-header lists.** The tell is a bold label and colon that restates the line:
    "**Performance:** Performance improved...". Convert those to prose. A bold lead-in that ends in
    a period, names the item, and is followed by genuinely new detail ("**Schema in TypeScript.**
    Tables live in one file.") is fine, not a tell.
17. **Title case headings.** Use sentence case (unless a repository linter or template requires
    otherwise).
18. **Decorative emojis.** Remove from headings and bullets.
19. **Curly quotes.** Use straight quotes.

### Communication artifacts

20. **Chatbot phrases.** "I hope this helps!", "Let me know if...", "Of course!", "Certainly!",
    "Found the smoking gun!" Remove.
22. **Sycophantic tone.** "Great question! You're absolutely right!" Respond directly.

### Filler

23. **Filler phrases.** "In order to" becomes "To". "Due to the fact that" becomes "Because". Delete
    "It is important to note that".
24. **Excessive hedging.** "could potentially possibly be argued that it might" becomes "may".
25. **Generic conclusions.** "The future looks bright." State specific plans or facts.

### Jargon

26. **Abstract metaphor nouns.** Substrate (base), wedge, wedge in (add), vector (way, method),
    locus, vantage, nexus, primitive as a noun, harness as a metaphor, surface as in "API surface",
    bedrock, scaffolding as a metaphor, modality, paradigm, gold-plating (more than the job needs),
    ratchet as a metaphor (the mechanism's real name, or a limit that only tightens), evacuate for
    moving code (move out), endgame (the last phase), north star, flywheel. These read as technical
    but usually have a plainer concrete word. Pick the concrete word (unless the word is an actual
    proper identifier in the codebase, such as the `agent-harness` plugin name).

### Plain speech

27. **Say what it does, not how it feels.** "the database stays close at hand", "SQL you can read",
    "types that follow your schema" name a feeling. The fix names the mechanism or a number:
    "`.toSQL()` returns the exact string sent to the database", "a column rename fails the build".
    Ask what the sentence tells the reader to do or know, then write that. If you can't restate it
    as a concrete instruction, fact, or number, cut it. One more check: if the sentence could appear
    unchanged in another project's docs, it says nothing about this one. Cut it.
28. **Shorten or split dense sentences.** If the reader has to backtrack to parse a sentence, break
    it in two or drop clauses. One idea per sentence.
29. **Active voice.** Prefer it. Catch "is/are/was/were + past participle" and name the actor:
    "queries are validated" becomes "the compiler validates queries", "the file is parsed by the
    loader" becomes "the loader parses the file". Passive is fine only when the actor is unknown or
    genuinely doesn't matter.
30. **Cut adverbs, or use a stronger verb.** "runs quickly" becomes "is fast" or the number, and
    "significantly improves" becomes the measured delta. An adverb propping up a weak verb means the
    verb is wrong.
31. **Prefer the plain word.** "utilize" and "leverage" become "use", "facilitate" becomes "help",
    "numerous" becomes "many", "in the event that" becomes "if". The fancier synonym is rarely
    clearer.
32. **Mannered prose.** Metaphor or flourish where a literal phrase exists: aphorisms ("wire it or
    delete it"), rhetorical fragments for effect, personified code ("the plan holds it"), figurative
    verbs ("rides along", "stands on"), stock framing phrases. "A dial worth turning" becomes "a
    parameter worth varying". Say what you mean. Rule 26 covers the metaphor nouns.
33. **Over-compression.** Dropped articles, verbless fragments, symbol-speak, and abbreviations that
    make the reader decode instead of read. "Parser rejects bad date -> exit 2, no write" becomes
    "The parser rejects a bad date, exits with code 2, and writes nothing." Write whole sentences
    with their articles and verbs, and spell out arrows and abbreviations.
