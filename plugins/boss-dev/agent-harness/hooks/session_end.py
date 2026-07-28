#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is optional


HOOKS_DIR = Path(__file__).resolve().parent
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from utils.harness_paths import session_log_dir


def perform_cleanup(session_id):
    """Perform optional cleanup tasks at session end."""
    cleanup_actions = []

    log_dir = session_log_dir(session_id)
    if log_dir.exists():
        # Clean up any .tmp files
        for tmp_file in log_dir.glob("*.tmp"):
            try:
                tmp_file.unlink()
                cleanup_actions.append(f"Removed temp file: {tmp_file.name}")
            except Exception:
                pass

    chat_file = log_dir / "chat.json" if log_dir.exists() else None
    if chat_file and chat_file.exists():
        try:
            # Check if file is older than 24 hours
            file_age = datetime.now().timestamp() - chat_file.stat().st_mtime
            if file_age > 86400:  # 24 hours in seconds
                chat_file.unlink()
                cleanup_actions.append("Removed stale chat.json (older than 24 hours)")
        except Exception:
            pass

    return cleanup_actions


def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument("--cleanup", action="store_true", help="Perform cleanup tasks at session end")
        args = parser.parse_args()

        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Extract session_id for session-scoped cleanup
        session_id = input_data.get("session_id", "unknown")

        # Perform cleanup if requested
        if args.cleanup:
            perform_cleanup(session_id)

        # Success
        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)


if __name__ == "__main__":
    main()
