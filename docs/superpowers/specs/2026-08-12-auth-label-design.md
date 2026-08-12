# Auth Label Design

**Date:** 2026-08-12  
**Status:** Approved

## Goal

Make the status-line auth field self-describing and avoid claiming that rate-limit data proves a
Max plan.

## Decision

`status_line_v10.py` will render the auth field as one of:

```text
[auth:subscription]
[auth:api]
[auth:pending]
```

The existing detection rules stay unchanged:

| `rate_limits` present | assistant `usage` seen | label |
| --- | --- | --- |
| yes | any | `[auth:subscription]` |
| no | yes | `[auth:api]` |
| no | no | `[auth:pending]` |

`subscription` covers Pro and Max sessions because the payload proves only that a subscription
rate-limit object exists. `pending` means the session has not produced enough data to distinguish an
API key from a subscription session. It does not report an unknown billing state.

The label remains the first status-line field. A representative row is:

```text
[auth:pending] [Sonnet 5] | cwd:~/dev/bossjones/boss-skills | branch:main | # [---------------] | 0.0% used | ~1.00M left | 32a21751-05cc-465c-998a-35dbb70f6d14 | $ $0.00
```

Existing colors remain: green for `subscription`, yellow for `api`, and dim for `pending`.

## Scope

Implementation updates:

- `format_auth_badge()` and its output assertions.
- v10 status-line documentation, including the auth-state table and explanatory prose.
- PR #68's legend and example row.

The change does not alter transcript scanning, rate-limit detection, context-window calculations,
cost calculation, status-line installation, or other status-line versions.

## Error Handling

The status line continues to fail open. Missing `rate_limits`, no transcript, unreadable transcript,
or no assistant usage render `[auth:pending]`. A malformed status-line payload continues through the
existing top-level error path.

## Validation

Tests must assert all three exact labels and preserve the existing detection matrix. Documentation
must state that `subscription` is an inference from rate-limit data, not a reported auth source.
