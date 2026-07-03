#!/usr/bin/env python3
"""Fake snyk-agent-scan: writes a sentinel file when invoked, then reports clean.

Used to assert the scanner was (or wasn't) actually invoked, e.g. when no
relevant staged files should have reached run_scan() at all.
"""

import json
import os
from pathlib import Path

sentinel = os.environ.get("FAKE_SCANNER_SENTINEL")
if sentinel:
    Path(sentinel).write_text("invoked")

print(json.dumps({"/fake/root": {"client": "x", "path": "/fake/root", "servers": [], "issues": [], "error": None}}))
raise SystemExit(0)
