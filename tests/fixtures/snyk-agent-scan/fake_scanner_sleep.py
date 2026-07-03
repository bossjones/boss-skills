#!/usr/bin/env python3
"""Fake snyk-agent-scan: sleeps to exercise the run_scan() timeout path."""

import time

time.sleep(5)
print("{}")
raise SystemExit(0)
