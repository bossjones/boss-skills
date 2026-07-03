#!/usr/bin/env python3
"""Fake snyk-agent-scan: a single Medium finding only (no Critical/High)."""

import json

print(
    json.dumps({
        "/fake/root/.claude/skills": {
            "client": "/fake/root/.claude/skills/example/SKILL.md",
            "path": "/fake/root/.claude/skills",
            "servers": [],
            "issues": [
                {
                    "code": "W011",
                    "message": "Third-party content exposure detected (risk: 0.5).",
                    "reference": [0, None],
                    "extra_data": {"risk_score": 0.5, "severity": "medium", "title": "Third-party content"},
                }
            ],
            "labels": [],
            "error": None,
        }
    })
)
raise SystemExit(0)
