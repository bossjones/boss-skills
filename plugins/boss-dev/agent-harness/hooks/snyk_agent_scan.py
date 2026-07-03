#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv",
# ]
# ///

"""SessionStart hook: advisory Snyk agent-scan of this project's skill artifacts.

Fail-open throughout: disabled, no token, no targets, scanner error/timeout, or an
import failure all result in a silent exit 0. Never blocks session start.
"""

import hashlib
import json
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is optional

sys.path.insert(0, str(Path(__file__).parent))
try:
    from utils.config import snyk_enabled, snyk_token
    from utils.snyk import ScanStatus, resolve_targets, run_scan, summarize
except ImportError:
    # utils/ is missing or broken — fail closed rather than crash the session.
    # snyk_enabled() always returns False here, so resolve_targets/run_scan/
    # summarize below are never actually invoked; they exist only so main()'s
    # references stay bound.
    class ScanStatus:  # type: ignore[no-redef]
        OK = object()

    def resolve_targets(root: Path) -> list[Path]:  # type: ignore[misc]
        return []

    def run_scan(targets: list[Path], *, token: str, timeout: float = 60.0):  # type: ignore[misc]
        raise RuntimeError("utils.snyk unavailable")

    def summarize(result: object) -> str:  # type: ignore[misc]
        return ""

    def snyk_enabled() -> bool:  # type: ignore[misc]
        return False

    def snyk_token() -> str:  # type: ignore[misc]
        return ""


THROTTLE_SECONDS = 6 * 3600


def _cache_path(project_root: Path) -> Path:
    cache_dir = Path(__file__).resolve().parent.parent / "logs" / "snyk-scan-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(str(project_root.resolve()).encode()).hexdigest()[:16]
    return cache_dir / f"{key}.json"


def _throttled(cache_file: Path) -> bool:
    try:
        data = json.loads(cache_file.read_text())
        return (time.time() - data.get("last_scan_ts", 0)) < THROTTLE_SECONDS
    except (OSError, json.JSONDecodeError, ValueError):
        return False


def _record_scan(cache_file: Path) -> None:
    try:
        cache_file.write_text(json.dumps({"last_scan_ts": time.time()}))
    except OSError:
        pass


def main() -> None:
    # Stdin JSON is read but not depended on (mirrors session_start.py) — a parse
    # failure here is not fatal to the scan itself.
    try:
        json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        pass

    if not snyk_enabled() or not snyk_token():
        sys.exit(0)

    project_root = Path.cwd()
    cache_file = _cache_path(project_root)
    if _throttled(cache_file):
        sys.exit(0)

    targets = resolve_targets(project_root)
    if not targets:
        _record_scan(cache_file)
        sys.exit(0)

    result = run_scan(targets, token=snyk_token(), timeout=60.0)
    _record_scan(cache_file)

    if result.status is ScanStatus.OK and any(result.severity_counts.values()):
        print(
            json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": summarize(result),
                }
            })
        )

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
