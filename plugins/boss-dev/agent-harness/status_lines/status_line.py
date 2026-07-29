#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import json
import os
import subprocess
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is optional


def get_git_branch():
    """Get current git branch if in a git repository."""
    try:
        result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_git_status():
    """Get git status indicators."""
    try:
        # Check if there are uncommitted changes
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            changes = result.stdout.strip()
            if changes:
                lines = changes.split("\n")
                return f"±{len(lines)}"
    except Exception:
        pass
    return ""


def generate_status_line(input_data):
    """Generate the status line based on input data."""
    parts = []

    # Model display name
    model_info = input_data.get("model", {})
    model_name = model_info.get("display_name", "Claude")
    parts.append(f"\033[36m[{model_name}]\033[0m")  # Cyan color

    # Current directory
    workspace = input_data.get("workspace", {})
    current_dir = workspace.get("current_dir", "")
    if current_dir:
        dir_name = os.path.basename(current_dir)
        parts.append(f"\033[34m📁 {dir_name}\033[0m")  # Blue color

    # Git branch and status
    git_branch = get_git_branch()
    if git_branch:
        git_status = get_git_status()
        git_info = f"🌿 {git_branch}"
        if git_status:
            git_info += f" {git_status}"
        parts.append(f"\033[32m{git_info}\033[0m")  # Green color

    # Version info (optional, smaller)
    version = input_data.get("version", "")
    if version:
        parts.append(f"\033[90mv{version}\033[0m")  # Gray color

    return " | ".join(parts)


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
        print("\033[31m[Claude] 📁 Unknown\033[0m")
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully - output basic status
        print("\033[31m[Claude] 📁 Error\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
