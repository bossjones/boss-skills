#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import argparse
import json
import os
import random
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is optional

# Resolve TTS config (plugin user-config with env fallback). Keep an inline
# fallback so the hook still runs if utils/config.py is ever missing.
sys.path.insert(0, str(Path(__file__).parent))
try:
    from utils.config import engineer_name, tts_enabled
except ImportError:

    def tts_enabled() -> bool:  # type: ignore[misc]
        return os.getenv("ENABLE_TTS", "1").strip().lower() not in {"0", "false", "no", "off"}

    def engineer_name() -> str:  # type: ignore[misc]
        return os.getenv("ENGINEER_NAME", "").strip()


def get_tts_script_path():
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


def announce_notification():
    """Announce that the agent needs user input."""
    try:
        if not tts_enabled():
            return  # TTS disabled

        tts_script = get_tts_script_path()
        if not tts_script:
            return  # No TTS scripts available

        # Get engineer name if available
        engineer_name_val = engineer_name()

        # Create notification message with 30% chance to include name
        if engineer_name_val and random.random() < 0.3:
            notification_message = f"{engineer_name_val}, your agent needs your input"
        else:
            notification_message = "Your agent needs your input"

        # Call the TTS script with the notification message
        subprocess.run(
            ["uv", "run", tts_script, notification_message],
            capture_output=True,  # Suppress output
            timeout=10,  # 10-second timeout
        )

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fail silently if TTS encounters issues
        pass
    except Exception:
        # Fail silently for any other errors
        pass


def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument("--notify", action="store_true", help="Enable TTS notifications")
        args = parser.parse_args()

        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Announce notification via TTS only if --notify flag is set
        # Skip TTS for the generic "Claude is waiting for your input" message
        if args.notify and input_data.get("message") != "Claude is waiting for your input":
            announce_notification()

        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)


if __name__ == "__main__":
    main()
