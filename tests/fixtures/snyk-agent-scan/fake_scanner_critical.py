#!/usr/bin/env python3
"""Fake snyk-agent-scan: mixed Critical + Medium findings, exits nonzero."""

import json

print(
    json.dumps({
        "/fake/root/.claude/skills": {
            "client": "/fake/root/.claude/skills/example/SKILL.md",
            "path": "/fake/root/.claude/skills",
            "servers": [],
            "issues": [
                {
                    "code": "E006",
                    "message": "Malicious code pattern detected (high risk: 1.00).",
                    "reference": [0, None],
                    "extra_data": {"risk_score": 1.0, "severity": "critical", "title": "Malicious code pattern"},
                },
                {
                    "code": "W011",
                    "message": "Third-party content exposure detected (risk: 0.5).",
                    "reference": [0, None],
                    "extra_data": {"risk_score": 0.5, "severity": "medium", "title": "Third-party content"},
                },
            ],
            "labels": [],
            "error": None,
        }
    })
)
raise SystemExit(2)
