#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is optional


HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from utils.harness_paths import data_dir


def _project_dir(input_data):
    """Return the project anchor supplied by the status-line payload."""
    workspace = input_data.get("workspace", {}) or {}
    return workspace.get("project_dir") or workspace.get("current_dir") or input_data.get("cwd") or os.getcwd()


def get_last_prompt(session_id, project_dir):
    """Get the last prompt for the current session."""
    session_file = data_dir(project_dir) / "sessions" / f"{session_id}.json"

    if not session_file.exists():
        return None, f"Session file {session_file} does not exist"

    try:
        with open(session_file, "r") as f:
            session_data = json.load(f)
            prompts = session_data.get("prompts", [])
            if prompts:
                return prompts[-1], None
            return None, "No prompts in session"
    except Exception as e:
        return None, f"Error reading session file: {str(e)}"


def generate_status_line(input_data):
    """Generate the status line showing the last prompt."""
    # Extract session ID from input data
    session_id = input_data.get("session_id", "unknown")

    # Get model name for prefix
    model_info = input_data.get("model", {})
    model_name = model_info.get("display_name", "Claude")

    # Get the last prompt
    prompt, error = get_last_prompt(session_id, _project_dir(input_data))

    if error:
        return f"\033[36m[{model_name}]\033[0m \033[90m💭 No recent prompt\033[0m"

    # Format the prompt for status line
    # Remove newlines and excessive whitespace
    prompt = " ".join(prompt.split())

    # Color coding based on prompt type
    if prompt.startswith("/"):
        # Command prompt - yellow
        prompt_color = "\033[33m"
        icon = "⚡"
    elif "?" in prompt:
        # Question - blue
        prompt_color = "\033[34m"
        icon = "❓"
    elif any(word in prompt.lower() for word in ["create", "write", "add", "implement", "build"]):
        # Creation task - green
        prompt_color = "\033[32m"
        icon = "💡"
    elif any(word in prompt.lower() for word in ["fix", "debug", "error", "issue"]):
        # Fix/debug task - red
        prompt_color = "\033[31m"
        icon = "🐛"
    elif any(word in prompt.lower() for word in ["refactor", "improve", "optimize"]):
        # Refactor task - magenta
        prompt_color = "\033[35m"
        icon = "♻️"
    else:
        # Default - white
        prompt_color = "\033[37m"
        icon = "💬"

    # Construct the status line
    status_line = f"\033[36m[{model_name}]\033[0m {icon} {prompt_color}{prompt}\033[0m"

    return status_line


def main():
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Generate status line
        status_line = generate_status_line(input_data)

        # Output the status line (first line of stdout becomes the status line)
        print(status_line)

        # Success
        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully - output basic status
        print("\033[31m[Claude] 💭 JSON Error\033[0m")
        sys.exit(0)
    except Exception as e:
        # Handle any other errors gracefully - output basic status
        print(f"\033[31m[Claude] 💭 Error: {str(e)}\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
