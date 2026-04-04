#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///

"""
Status Line v8 - Token Usage with Cache Stats
Display: [Model] In: 15.2k | Out: 4.5k | Cache: ^5k v2k
Show input/output tokens and cache creation/read stats
"""

import json
import sys

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


def format_tokens(tokens):
    """Format token count in human-readable format."""
    if tokens is None or tokens == 0:
        return "0"
    if tokens < 1000:
        return str(int(tokens))
    elif tokens < 10000:
        return f"{tokens / 1000:.1f}k"
    elif tokens < 1000000:
        return f"{tokens / 1000:.0f}k"
    else:
        return f"{tokens / 1000000:.1f}M"


def generate_status_line(input_data):
    """Generate the token usage status line."""
    # Get model name
    model_info = input_data.get("model", {})
    model_name = model_info.get("display_name", "Claude")

    # Get context window data
    context_data = input_data.get("context_window", {})
    total_input = context_data.get("total_input_tokens", 0) or 0
    total_output = context_data.get("total_output_tokens", 0) or 0

    # Get current usage for cache stats
    current_usage = context_data.get("current_usage", {}) or {}
    cache_creation = current_usage.get("cache_creation_input_tokens", 0) or 0
    cache_read = current_usage.get("cache_read_input_tokens", 0) or 0

    # Format token counts
    input_str = format_tokens(total_input)
    output_str = format_tokens(total_output)
    cache_create_str = format_tokens(cache_creation)
    cache_read_str = format_tokens(cache_read)

    # Build status line
    parts = []

    # Model name in cyan
    parts.append(f"{CYAN}[{model_name}]{RESET}")

    # Chart emoji
    parts.append(f"{MAGENTA}#{RESET}")

    # Input tokens (incoming arrow)
    parts.append(f"In: {GREEN}{input_str}{RESET}")

    # Output tokens (outgoing)
    parts.append(f"Out: {YELLOW}{output_str}{RESET}")

    # Cache stats with up/down arrows
    cache_str = f"Cache: {BLUE}^{cache_create_str}{RESET} {DIM}v{cache_read_str}{RESET}"
    parts.append(cache_str)

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
        print(f"{RED}[Claude] # Error: Invalid JSON{RESET}")
        sys.exit(0)
    except Exception as e:
        # Handle any other errors gracefully
        print(f"{RED}[Claude] # Error: {str(e)}{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
