#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv",
# ]
# ///

"""
Status Line v10 - Context Window Usage + Adobe-priced Session Cost
Display: [Model] | # [###---] | 42.5% used | ~115k left | session_id | $ $0.0421
Like v6 but appends a running cost total computed from the transcript using
Adobe-discounted Anthropic/Bedrock pricing.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


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


# Adobe-discounted prices (USD per 1M tokens), global rates: (input, output)
ADOBE_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (0.90, 4.50),
    "claude-sonnet-4-5": (2.70, 13.50),
    "claude-opus-4-5": (4.50, 22.50),
    "claude-opus-4-6": (4.50, 22.50),
    # Opus 4.7 list price not yet published; assume same list as 4.6 ($5/$25)
    # with the same 10% Adobe discount → $4.50/$22.50.
    "claude-opus-4-7": (4.50, 22.50),
}
# Fallback for unknown/newer models — opus-tier global Adobe rates
DEFAULT_PRICING: tuple[float, float] = (4.50, 22.50)

# Standard Anthropic cache multipliers applied on top of input price
CACHE_CREATION_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER = 0.10


def get_usage_color(percentage: float) -> str:
    """Get color based on usage percentage."""
    if percentage < 50:
        return GREEN
    elif percentage < 75:
        return YELLOW
    elif percentage < 90:
        return RED
    else:
        return "\033[91m"  # Bright red for critical


def create_progress_bar(percentage: float, width: int = 15) -> str:
    """Create a visual progress bar."""
    filled = int((percentage / 100) * width)
    empty = width - filled

    color = get_usage_color(percentage)

    bar = f"{color}{'#' * filled}{DIM}{'-' * empty}{RESET}"
    return f"[{bar}]"


def format_tokens(tokens: float | int | None) -> str:
    """Format token count in human-readable format."""
    if tokens is None:
        return "0"
    if tokens < 1000:
        return str(int(tokens))
    elif tokens < 1000000:
        return f"{tokens / 1000:.1f}k"
    else:
        return f"{tokens / 1000000:.2f}M"


def format_cost(cost_usd: float | None) -> str:
    """Format cost with appropriate precision."""
    if cost_usd is None or cost_usd == 0:
        return "$0.00"
    elif cost_usd < 0.01:
        return f"${cost_usd:.4f}"
    elif cost_usd < 1.00:
        return f"${cost_usd:.3f}"
    else:
        return f"${cost_usd:.2f}"


_MODEL_SUFFIX_RE = re.compile(r"\[[^\]]*\]|-\d{8}$")


def normalize_model_id(model_id: str) -> str:
    """Strip variant tags like '[1m]' and date suffixes like '-20251001'."""
    if not model_id:
        return ""
    cleaned = _MODEL_SUFFIX_RE.sub("", model_id).strip()
    return cleaned


def get_pricing(model_id: str) -> tuple[float, float]:
    """Look up Adobe pricing for a model id, falling back to opus-tier rates."""
    return ADOBE_PRICING.get(normalize_model_id(model_id), DEFAULT_PRICING)


def shorten_cwd(path: str) -> str:
    """Collapse $HOME to ~ for a compact cwd display."""
    if not path:
        return "~"
    home = str(Path.home())
    if path.startswith(home):
        return "~" + path[len(home) :]
    return path


def get_git_branch(cwd: str) -> str | None:
    """Return the current git branch for `cwd`, or None if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "-C", cwd or ".", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            if branch:
                return branch
    except Exception:
        pass
    return None


def compute_session_cost(transcript_path: str | None) -> float:
    """Compute total session cost (USD) from a transcript JSONL using Adobe prices.

    Returns 0.0 on any failure so the status line never breaks.
    """
    if not transcript_path:
        return 0.0

    path = Path(transcript_path)
    if not path.is_file():
        return 0.0

    total = 0.0
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                message = entry.get("message")
                if not isinstance(message, dict):
                    continue
                usage = message.get("usage")
                if not isinstance(usage, dict):
                    continue

                model_id = message.get("model", "") or ""
                in_price, out_price = get_pricing(model_id)

                input_tokens = usage.get("input_tokens", 0) or 0
                cache_creation = usage.get("cache_creation_input_tokens", 0) or 0
                cache_read = usage.get("cache_read_input_tokens", 0) or 0
                output_tokens = usage.get("output_tokens", 0) or 0

                total += (
                    input_tokens * in_price
                    + cache_creation * in_price * CACHE_CREATION_MULTIPLIER
                    + cache_read * in_price * CACHE_READ_MULTIPLIER
                    + output_tokens * out_price
                ) / 1_000_000
    except OSError:
        return 0.0

    return total


def generate_status_line(input_data: dict) -> str:
    """Generate the context window usage status line with Adobe-priced cost."""
    model_info = input_data.get("model", {}) or {}
    model_name = model_info.get("display_name", "Claude")

    session_id = input_data.get("session_id", "") or "--------"

    workspace = input_data.get("workspace", {}) or {}
    current_dir = workspace.get("current_dir") or input_data.get("cwd") or os.getcwd()

    context_data = input_data.get("context_window", {}) or {}
    used_percentage = context_data.get("used_percentage", 0) or 0
    context_window_size = context_data.get("context_window_size", 200000) or 200000

    remaining_tokens = int(context_window_size * ((100 - used_percentage) / 100))

    usage_color = get_usage_color(used_percentage)

    transcript_path = input_data.get("transcript_path", "")
    try:
        total_cost = compute_session_cost(transcript_path)
    except Exception:
        total_cost = 0.0

    parts: list[str] = []

    parts.append(f"{CYAN}[{model_name}]{RESET}")

    parts.append(f"{BLUE}cwd:{shorten_cwd(current_dir)}{RESET}")

    branch = get_git_branch(current_dir)
    parts.append(f"{GREEN}branch:{branch if branch else 'n/a'}{RESET}")

    progress_bar = create_progress_bar(used_percentage)
    parts.append(f"{MAGENTA}#{RESET} {progress_bar}")

    parts.append(f"{usage_color}{used_percentage:.1f}%{RESET} used")

    tokens_left_str = format_tokens(remaining_tokens)
    parts.append(f"{BLUE}~{tokens_left_str} left{RESET}")

    parts.append(f"{DIM}{session_id}{RESET}")

    parts.append(f"{YELLOW}${RESET} {BRIGHT_WHITE}{format_cost(total_cost)}{RESET}")

    return " | ".join(parts)


def main() -> None:
    try:
        input_data = json.loads(sys.stdin.read())
        status_line = generate_status_line(input_data)
        print(status_line)
        sys.exit(0)
    except json.JSONDecodeError:
        print(f"{RED}[Claude] # Error: Invalid JSON{RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"{RED}[Claude] # Error: {e!s}{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
