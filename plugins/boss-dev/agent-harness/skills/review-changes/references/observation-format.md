# Finding format

Every lens returns exactly this JSON — no prose before or after it.

```json
{
  "observations": [
    {
      "theme": "claims | consistency | structure | cross-refs | placement | disclosure | code",
      "category": "<from the lens's category list>",
      "priority": "CRITICAL | HIGH | MEDIUM | LOW",
      "confidence": "HIGH | MEDIUM | LOW",
      "uncertainty_reason": "required when confidence is MEDIUM or LOW",
      "location": { "file": "specs/skills-lifecycle-deliverables.md", "line": 612, "end_line": 618 },
      "observation": "What is wrong — one sentence, `code refs` in backticks",
      "concern": "What breaks, under what conditions — concrete, not vague",
      "evidence": [
        "CLAUDE.md §Placement: 'new skills live under skills/<name>/'",
        "Counted 19 rows in the table; the prose at [604] says 21"
      ],
      "suggestion": {
        "description": "What to change",
        "replaces": "exact text copied from the annotated patch",
        "code": "the replacement"
      },
      "related_to": [],
      "also_flagged_under": []
    }
  ],
  "summary": "N findings: 1 claims (HIGH), 2 consistency (MEDIUM)"
}
```

## The two axes are independent

**`priority` is how bad it is. `confidence` is how sure you are.** Never collapse them. A
CRITICAL/LOW is a legitimate finding ("this would misstate the plan of record *if* the
2026-08-26 standup decision holds, and I could not confirm it did"); so is a LOW/HIGH
("definitely a stale section reference").

| `priority` | Use for |
|---|---|
| CRITICAL | A live credential in tracked content; a weakened security guard; an exit-code or public-API contract change CI gates on; a false claim that would be acted on irreversibly (a ticket filed, a doc published) |
| HIGH | A stale count, key, or attribution that a reader will act on; a repo rule broken outright; two contradicting statements where one is a contract (owner, date, decision, scope) |
| MEDIUM | A broken anchor or link; a missing index entry; an inferred claim written as settled fact; docs not updated with a behaviour change; a test gap on new CLI behaviour |
| LOW | Minor, unlikely to bite; a stale phrase left from an earlier revision; a leftover pointer with no action attached |

| `confidence` | Meaning |
|---|---|
| HIGH | Verified it is real and not addressed elsewhere in the diff |
| MEDIUM | Likely, but something specific is unverified — name it in `uncertainty_reason` |
| LOW | Possible; may be settled by a source you could not reach, or by a convention |

`uncertainty_reason` is not a formality — the challenge pass reads it to know **where to
look**. "Unsure" is useless; "did not confirm the issue type in Jira" tells the challenger
exactly what to check, and is how a MEDIUM finding gets *raised* to HIGH rather than dropped.

## `location` is a diff line, not a file line

`location.line` must be a number that appeared as `[N]` in the annotated patch for
`location.file`. A file read or a search result shows **file** line numbers; the patch shows the
line number in the **new** file *as annotated*. On a large document these diverge badly, and
Step 4 drops the finding with no appeal. When the real problem sits outside the diff, anchor to
the diff line that *creates* it, or drop the finding — never to an unrelated nearby line.

## `evidence` is required and must be non-empty

A finding whose evidence is only your own assertion is not a finding. Quote the rule by path,
quote both sides of a contradiction with their line numbers, or state the lookup you ran and
what it returned.
