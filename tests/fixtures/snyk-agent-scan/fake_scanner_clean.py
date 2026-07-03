#!/usr/bin/env python3
"""Fake snyk-agent-scan: clean scan, no issues. Mirrors the real --json shape."""

import json

print(
    json.dumps({
        "/fake/root/.claude/skills": {
            "client": "/fake/root/.claude/skills/example/SKILL.md",
            "path": "/fake/root/.claude/skills",
            "servers": [],
            "issues": [],
            "labels": [],
            "error": None,
        }
    })
)
raise SystemExit(0)
