#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import argparse
import json
import subprocess
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


def debug_log(message: str, session_id: str) -> None:
    """Write a subagent-specific debug message."""
    try:
        debug_path = session_log_dir(session_id) / "subagent_debug.log"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat()
        with debug_path.open("a") as f:
            f.write(f"[{timestamp}] [START] {message}\n")
    except Exception:
        pass


def get_tts_script_path() -> str | None:
    """
    Determine which TTS script to use.
    Uses the offline pyttsx3 backend (no API key required).
    """
    script_dir = Path(__file__).parent
    tts_dir = script_dir / "utils" / "tts"

    pyttsx3_script = tts_dir / "pyttsx3_tts.py"
    if pyttsx3_script.exists():
        return str(pyttsx3_script)

    return None


def announce_subagent_start(message: str = "Subagent Started") -> None:
    """Announce subagent start using the best available TTS service.

    Args:
        message: The message to announce via TTS
    """
    try:
        tts_script = get_tts_script_path()
        if not tts_script:
            return  # No TTS scripts available

        # Call the TTS script with the provided message
        subprocess.run(
            ["uv", "run", tts_script, message],
            capture_output=True,  # Suppress output
            timeout=10,  # 10-second timeout
        )

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fail silently if TTS encounters issues
        pass
    except Exception:
        # Fail silently for any other errors
        pass


def main() -> None:
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(
            description="SubagentStart hook - logs and optionally announces subagent spawn events"
        )
        parser.add_argument("--notify", action="store_true", help="Enable TTS announcement when subagent starts")
        args = parser.parse_args()

        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        # Extract fields for announcement and session-scoped diagnostics.
        agent_id = input_data.get("agent_id", "unknown")
        agent_type = input_data.get("agent_type", "unknown")
        session_id = input_data.get("session_id", "unknown")

        debug_log(f"SubagentStart: agent_id={agent_id}, agent_type={agent_type}", session_id)

        # Announce subagent start via TTS (only if --notify flag is set)
        if args.notify:
            debug_log(f"=== SubagentStart for agent: {agent_id} ===", session_id)
            debug_log(f"agent_type: {agent_type}", session_id)

            # Create announcement message
            if agent_type and agent_type != "unknown":
                announcement = f"{agent_type} agent started"
            else:
                announcement = "Subagent started"

            debug_log(f"Announcing: {announcement}", session_id)
            announce_subagent_start(announcement)

        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)


if __name__ == "__main__":
    main()
