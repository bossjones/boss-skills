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


def get_session_data(session_id, project_dir):
    """Get session data including agent name, prompts, and extras."""
    session_file = data_dir(project_dir) / "sessions" / f"{session_id}.json"

    if not session_file.exists():
        return None, f"Session file {session_file} does not exist"

    try:
        with open(session_file, "r") as f:
            session_data = json.load(f)
            return session_data, None
    except Exception as e:
        return None, f"Error reading session file: {str(e)}"


def truncate_prompt(prompt, max_length=75):
    """Truncate prompt to specified length."""
    # Remove newlines and excessive whitespace
    prompt = " ".join(prompt.split())

    if len(prompt) > max_length:
        return prompt[: max_length - 3] + "..."
    return prompt


def get_prompt_icon(prompt):
    """Get icon based on prompt type."""
    if prompt.startswith("/"):
        return "⚡"
    elif "?" in prompt:
        return "❓"
    elif any(word in prompt.lower() for word in ["create", "write", "add", "implement", "build"]):
        return "💡"
    elif any(word in prompt.lower() for word in ["fix", "debug", "error", "issue"]):
        return "🐛"
    elif any(word in prompt.lower() for word in ["refactor", "improve", "optimize"]):
        return "♻️"
    else:
        return "💬"


def format_extras(extras):
    """Format extras dictionary into a compact string."""
    if not extras:
        return None

    # Format each key-value pair
    pairs = []
    for key, value in extras.items():
        # Truncate value if too long
        str_value = str(value)
        if len(str_value) > 20:
            str_value = str_value[:17] + "..."
        pairs.append(f"{key}:{str_value}")

    return " ".join(pairs)


def generate_status_line(input_data):
    """Generate the status line with agent name, most recent prompt, and extras."""
    # Extract session ID from input data
    session_id = input_data.get("session_id", "unknown")

    # Get model name
    model_info = input_data.get("model", {})
    model_name = model_info.get("display_name", "Claude")

    # Get session data
    session_data, error = get_session_data(session_id, _project_dir(input_data))

    if error:
        return f"\033[36m[{model_name}]\033[0m \033[90m💭 No session data\033[0m"

    # Extract agent name, prompts, and extras
    agent_name = session_data.get("agent_name", "Agent")
    prompts = session_data.get("prompts", [])
    extras = session_data.get("extras", {})

    # Build status line components
    parts = []

    # Agent name - Bright Red
    parts.append(f"\033[91m[{agent_name}]\033[0m")

    # Model name - Blue
    parts.append(f"\033[34m[{model_name}]\033[0m")

    # Most recent prompt
    if prompts:
        current_prompt = prompts[-1]
        icon = get_prompt_icon(current_prompt)
        truncated = truncate_prompt(current_prompt, 100)
        parts.append(f"{icon} \033[97m{truncated}\033[0m")
    else:
        parts.append("\033[90m💭 No prompts yet\033[0m")

    # Add extras if they exist
    if extras:
        extras_str = format_extras(extras)
        if extras_str:
            # Display extras in cyan with brackets
            parts.append(f"\033[36m[{extras_str}]\033[0m")

    # Join with separator
    status_line = " | ".join(parts)

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
        print("\033[31m[Agent] [Claude] 💭 JSON Error\033[0m")
        sys.exit(0)
    except Exception as e:
        # Handle any other errors gracefully - output basic status
        print(f"\033[31m[Agent] [Claude] 💭 Error: {str(e)}\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
