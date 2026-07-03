#!/usr/bin/env python3
"""Fake snyk-agent-scan: one High finding. Exits 1 to prove gating ignores exit codes."""

import json

print(
    json.dumps({
        "/fake/root/.claude/skills": {
            "client": "/fake/root/.claude/skills/example/SKILL.md",
            "path": "/fake/root/.claude/skills",
            "servers": [],
            "issues": [
                {
                    "code": "E004",
                    "message": "Potential prompt injection detected (high risk: 1.00).",
                    "reference": [0, None],
                    "extra_data": {
                        "risk_score": 1.0,
                        "severity": "high",
                        "title": "Potential prompt injection detected",
                    },
                }
            ],
            "labels": [],
            "error": None,
        }
    })
)
raise SystemExit(1)
