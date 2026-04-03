#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///

"""
Status Line v7 - Session Duration Timer
Display: [Model] @ Session: 12m 34s | Started: 2:30 PM
Track session start time, show elapsed duration
"""

import json
import sys
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is optional


# ANSI color codes
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BRIGHT_WHITE = "\033[97m"
DIM = "\033[90m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


# Session tracking file
SESSION_TIMES_FILE = Path.home() / ".claude" / "session_times.json"


def get_session_start_time(session_id):
    """Get or create the session start time."""
    # Ensure directory exists
    SESSION_TIMES_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load existing session times
    session_times = {}
    if SESSION_TIMES_FILE.exists():
        try:
            with open(SESSION_TIMES_FILE, "r") as f:
                session_times = json.load(f)
        except (json.JSONDecodeError, ValueError):
            session_times = {}

    # Check if session already has a start time
    if session_id in session_times:
        return datetime.fromisoformat(session_times[session_id])

    # Create new start time for this session
    start_time = datetime.now()
    session_times[session_id] = start_time.isoformat()

    # Clean up old sessions (keep only last 50)
    if len(session_times) > 50:
        # Sort by time and keep most recent 50
        sorted_sessions = sorted(session_times.items(), key=lambda x: x[1], reverse=True)
        session_times = dict(sorted_sessions[:50])

    # Save back to file
    try:
        with open(SESSION_TIMES_FILE, "w") as f:
            json.dump(session_times, f, indent=2)
    except Exception:
        pass  # Ignore write errors

    return start_time


def format_elapsed_time(start_time):
    """Format elapsed time since start."""
    elapsed = datetime.now() - start_time
    total_seconds = int(elapsed.total_seconds())

    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def format_start_time(start_time):
    """Format the start time in 12-hour format."""
    return start_time.strftime("%I:%M %p").lstrip("0")


def get_duration_color(start_time):
    """Get color based on session duration."""
    elapsed = datetime.now() - start_time
    total_minutes = elapsed.total_seconds() / 60

    if total_minutes < 30:
        return GREEN
    elif total_minutes < 60:
        return YELLOW
    elif total_minutes < 120:
        return MAGENTA
    else:
        return RED


def generate_status_line(input_data):
    """Generate the session duration status line."""
    # Get model name
    model_info = input_data.get("model", {})
    model_name = model_info.get("display_name", "Claude")

    # Get session ID
    session_id = input_data.get("session_id", "default")

    # Get session start time
    start_time = get_session_start_time(session_id)

    # Format times
    elapsed_str = format_elapsed_time(start_time)
    started_str = format_start_time(start_time)
    duration_color = get_duration_color(start_time)

    # Build status line
    parts = []

    # Model name in cyan
    parts.append(f"{CYAN}[{model_name}]{RESET}")

    # Clock emoji and session duration
    parts.append(f"{BLUE}@{RESET} Session: {duration_color}{elapsed_str}{RESET}")

    # Start time
    parts.append(f"Started: {DIM}{started_str}{RESET}")

    return " | ".join(parts)


def main():
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Generate status line
        status_line = generate_status_line(input_data)

        # Output the status line
        print(status_line)

        # Success
        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        print(f"{RED}[Claude] @ Error: Invalid JSON{RESET}")
        sys.exit(0)
    except Exception as e:
        # Handle any other errors gracefully
        print(f"{RED}[Claude] @ Error: {str(e)}{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
