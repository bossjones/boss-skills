# Lens: claims

`theme: "claims"`. Whether every concrete assertion the diff makes is actually true.

Run every gate in `quality-gates.md` before reporting. Return only the JSON in
`observation-format.md`.

**This is the highest-yield lens in the set.** Everything here is checkable, and the cheapest
place to catch a false claim is before it reaches a PR, a published doc, or a teammate's review
queue — someone reading it later will not re-derive its numbers.

## Domain

Counts, dates, names, ticket keys, URLs, file paths, quoted sources, ownership attributions,
status assertions, and claims about what code or a system actually does.

**Not yours:** two statements inside the doc contradicting each other (`consistency`),
whether a link *resolves* as opposed to whether the claim is *true* (`cross-refs`), section
numbering (`structure`).

## What to check specifically

**Counts.** "the 25 tools", "21 child items", "15 decisions", "three services" —
**count them**. A stale count is a real and common finding. Say how you counted.

**Ticket keys.** If the repo profile (`references/repo-profile.md`) names an issue-tracker
pattern and lookup, every key matching that pattern must exist and be the issue type and state
the doc claims. Use the lookup command or MCP tool the profile names, or whatever tracker
integration is present in the session; if none is available, say so in the evidence rather than
asserting the key is wrong. A doc that calls something an Epic when the tracker has it as a
Story is a finding — teams plan off that distinction. **Never write to the tracker from this
lens.**

**Repos, PRs, and URLs.** A GitHub link must name a repo that exists and a PR number in *that*
repo. Verify with `gh` if available, or the file itself, rather than pattern-matching the URL.

**Claims about what code elsewhere in the repo does — delegate, do not grep inline.** A claim
like "the CLI exposes N subcommands" or "the SDK still has method X" should go to a plain
subagent dispatched for that one question, which returns a compact verdict with a file citation
without blowing this lens's own context. Use Scout MCP tools (`mcp__scout__keyword_search`,
`mcp__scout__go_to_definition`) if present in the session; otherwise `Grep`/`Glob`. If neither
path is available, say so in your evidence — do not claim an index-backed answer you did not get.

**The claim-tagging contract, if the repo has one.** Some repos tag claims with a
source/confidence convention (a legend explaining what each tag means, usually near the top of
the document). The repo profile's `## Claim conventions` section names it if one exists. Where
it does:

| Shape | Finding |
|---|---|
| A claim tagged as sourced/verified with no matching entry in the doc's own sources section | HIGH — the tag asserts a source that is not there |
| A claim tagged as inferred/unverified but written as settled fact in the surrounding prose | MEDIUM — the tag says "sanity-check me", the prose says "this is so" |
| A claim tagged as open/TODO absent from the doc's own tracking section for open items | MEDIUM — an open item nobody will find |
| An untagged factual claim in a doc that tags everything else | LOW — check it, then say it is untagged |

Where no such convention is discovered, do not invent one — check claims on their merits instead.

**Attribution.** A decision, an ownership assignment, or a quote attributed to a named person
must trace to a source the document cites or a linked transcript. Misattributing a decision is
an expensive prose defect — it tends to get repeated downstream before anyone checks. Weight it
HIGH when the attribution assigns work or settles a question.

**Status assertions.** "Done", "merged", "decided", "blocked on X" — check the underlying
artifact. A doc that says a PR merged when it is still draft misstates the plan of record.

**Dates.** A relative date ("last week", "the recent standup") in a durable doc is worth flagging
if the repo's own conventions (discovered rules, or the profile) ask for absolute dates. A stated
date that contradicts a changelog or history section is a HIGH regardless.

## Categories

`stale-count`, `nonexistent-tracker-key`, `wrong-tracker-type-or-state`, `nonexistent-reference`,
`misattributed-citation`, `unsourced-claim`, `inference-as-fact`, `contradicted-by-source`,
`stale-status`, `relative-date`, `unverified-code-claim`.

## Evidence bar

**Quote both sides.** For a count: the number claimed and the number you counted, with how you
counted it. For a tracker key: the key and what the lookup returned. For a code claim: the
subagent's verdict and the file it cited. A claim finding with no counter-evidence is not a
finding — it is a doubt, and doubts belong in `uncertainty_reason` at MEDIUM.

## Do not report

A claim you merely find surprising. An item tagged open/TODO that is genuinely open — the tag
already says so. A number the doc explicitly marks as an estimate. Typos in a name. A source you
could not reach because a tool was unavailable — say so at LOW with the reason, do not assert the
claim is false.
