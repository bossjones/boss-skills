# Lens: consistency

`theme: "consistency"`. Two statements in the same change that cannot both be true.

Run every gate in `quality-gates.md`. Return only the JSON in `observation-format.md`.

This class is invisible to every linter and to the renderer. **Only a cross-read catches it**,
and in a document of any real length nobody performs that cross-read by hand — which is exactly
why the contradictions survive to the reader.

## Domain

Internal contradictions within the changed document, and between the changed document and a
canonical doc it declares itself downstream of (if the repo has that convention).

**Not yours:** whether a single claim is true against the outside world (`claims`), broken
links and anchors (`cross-refs` / `structure`).

## What to cross-read

**Table versus prose.** A master table that assigns an owner the body assigns to someone else. A
row marked "blocked" whose section says work has started. A scope column that contradicts the
section it points at. When a table and its surrounding prose disagree, say which one downstream
readers will act on.

**Header versus body.** A `> **Status:**` line, an owner line, or a "last reconciled" date that
a changelog or the body contradicts. A doc that calls itself DRAFT while a section announces a
decision as final.

**Decision state.** The same decision recorded as settled in one section and open in another —
a common contradiction in specs and design docs, because sections get revised independently.
Check every decision named in an open-items section against the body.

**Ticket scope.** The same epic or ticket described with two different scopes in two places. Two
sections that each claim to own the same deliverable. Two sections assigning the same work to
different teams.

**Terminology.** A doc that pins a term's meaning in a terminology section and then uses a
different name for the same thing later, or the same name for something different.

**Canonical-versus-downstream.** Some repos declare a canonical source for a piece of content in
its own header (a note that a wiki page, generated site, or other copy is downstream of this
file). A change to a downstream copy that contradicts the canonical file is a finding: cite both
paths and say which one wins **by its own declaration**, not by your preference. The repo
profile's `## Downstream renders` section may name these relationships explicitly.

**Rule files against each other.** If discovery (Step 2 / `references/repo-profile.md`) found
more than one rule file with *different* blob ids restating the same conventions — for example a
`CLAUDE.md` and a separate `AGENTS.md` that each carry their own copy of a directory convention —
a rule edited in one that the other now contradicts is a HIGH. Two agents (or two humans) reading
two different rulebooks is a real failure mode. Symlinked rule files (same blob id) do not count;
that is one file, not two disagreeing ones.

**Numeric self-consistency.** A total that does not equal the sum of its parts. A table with N
rows described in prose as having M. A percentage set that does not close.

## Priority

HIGH when the two statements are a **contract**: an owner, a date, a decision, a ticket scope, a
deliverable boundary. Someone will act on one of them and be wrong.

MEDIUM when the contradiction is descriptive — two framings of the same thing that a careful
reader could reconcile.

LOW when it is a leftover phrase from an earlier revision that no longer matches, with no action
attached.

## Categories

`table-vs-prose`, `header-vs-body`, `decision-state-conflict`, `ownership-conflict`,
`scope-conflict`, `terminology-drift`, `canonical-vs-downstream`, `numeric-mismatch`,
`stale-revision-remnant`.

## Evidence bar

**Both statements, both with their line numbers**, and one sentence on which one a downstream
reader would act on. "This section feels inconsistent with the rest" is not a finding. If only
one of the two statements is inside the diff, anchor to the diff line that *creates* the
contradiction — never to an unrelated nearby line to smuggle it in.

## Do not report

Two statements at different altitudes that are both true (a summary and its detail). Deliberate
restatement for emphasis. A tension the doc explicitly names and leaves open. A preference for
one of two compatible framings.
