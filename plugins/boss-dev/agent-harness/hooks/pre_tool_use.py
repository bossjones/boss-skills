#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# ///

from __future__ import annotations

import json
import re
import sys
from collections.abc import Generator
from pathlib import Path


def is_dangerous_rm_command(command):
    """
    Comprehensive detection of dangerous rm commands.
    Matches various forms of rm -rf and similar destructive patterns.
    """
    # Normalize command by removing extra spaces and converting to lowercase
    normalized = " ".join(command.lower().split())

    # Pattern 1: Standard rm -rf variations
    patterns = [
        r"\brm\s+.*-[a-z]*r[a-z]*f",  # rm -rf, rm -fr, rm -Rf, etc.
        r"\brm\s+.*-[a-z]*f[a-z]*r",  # rm -fr variations
        r"\brm\s+--recursive\s+--force",  # rm --recursive --force
        r"\brm\s+--force\s+--recursive",  # rm --force --recursive
        r"\brm\s+-r\s+.*-f",  # rm -r ... -f
        r"\brm\s+-f\s+.*-r",  # rm -f ... -r
    ]

    # Check for dangerous patterns
    for pattern in patterns:
        if re.search(pattern, normalized):
            return True

    # Pattern 2: Check for rm with recursive flag targeting dangerous paths.
    # Each pattern matches the dangerous target as a whole argument so that
    # ordinary relative paths (e.g. "rm -r ./build/output") are not flagged.
    dangerous_paths = [
        r"\s/\s*$",  # rm -rf /            (root)
        r"\s/\s+",  # rm -rf / home/user  (root as a separate argument)
        r"\s/\*",  # rm -rf /*            (everything under root)
        r"\s~\s*$",  # rm -rf ~            (home directory)
        r"\s~/",  # rm -rf ~/...         (home subtree)
        r"\$home\b",  # rm -rf $HOME         (home env var; `normalized` is lowercased)
        r"\.\.",  # parent-directory references (.. , ../..)
        r"\s\*\s*$",  # rm -rf *             (bare wildcard)
        r"\s\./?\s*$",  # rm -rf . or ./       (current directory)
    ]

    if re.search(r"\brm\s+.*-[a-z]*r", normalized):  # If rm has recursive flag
        for path in dangerous_paths:
            if re.search(path, normalized):
                return True

    return False


def is_env_file_access(tool_name, tool_input):
    """
    Check if any tool is trying to access .env files containing sensitive data.
    """
    if tool_name in ["Read", "Edit", "MultiEdit", "Write", "Bash"]:
        # Check file paths for file-based tools
        if tool_name in ["Read", "Edit", "MultiEdit", "Write"]:
            file_path = tool_input.get("file_path", "")
            # Block real .env secret files, but allow the secret-free committed
            # templates (.env.sample / .env.example).
            if ".env" in file_path and not file_path.endswith((".env.sample", ".env.example")):
                return True

        # Check bash commands for .env file access
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            # Detect any reference to a .env file (e.g. "source .env", "less .env",
            # "cat ./.env"), but allow the secret-free templates (.env.sample /
            # .env.example). A plain `\b` before the dot fails when the dot follows
            # whitespace, so anchor on a lookbehind for a non-word/path boundary
            # instead. This single pattern subsumes the per-command checks
            # (cat/echo/touch/cp/mv/source/...).
            env_patterns = [
                r"(?<![\w.])\.env(?![\w])(?!\.sample)(?!\.example)",
            ]

            for pattern in env_patterns:
                if re.search(pattern, command):
                    return True

    return False


# BLOCKER-class Unicode codepoint sets, mirrored inline from
# scripts/validate-unicode-hygiene.py (TAG_RANGE + BIDI_CONTROLS) so the hook stays
# fast and free of a fragile cross-tree import to a hyphen-named script. Both sets
# are fixed by the Unicode standard; that script is their canonical definition.
UNICODE_TAG_RANGE: range = range(0xE0000, 0xE0080)
UNICODE_BIDI_CONTROLS: frozenset[int] = frozenset({
    0x202A,
    0x202B,
    0x202C,
    0x202D,
    0x202E,
    0x2066,
    0x2067,
    0x2068,
    0x2069,
})


def _iter_edit_content(tool_name: str, tool_input: dict[str, object]) -> Generator[str, None, None]:
    """Yield each chunk of proposed content for a Write/Edit/MultiEdit call."""
    if tool_name == "Write":
        yield tool_input.get("content", "")
    elif tool_name == "Edit":
        yield tool_input.get("new_string", "")
    elif tool_name == "MultiEdit":
        for edit in tool_input.get("edits", []) or []:
            yield edit.get("new_string", "")


def find_blocker_unicode(tool_name: str, tool_input: dict[str, object]) -> tuple[int, int, str] | None:
    """Scan proposed Write/Edit/MultiEdit content for BLOCKER-class Unicode.

    Returns (codepoint, offset, label) for the first invisible tag character or
    bidirectional control character found, or None when the content is clean.
    """
    for content in _iter_edit_content(tool_name, tool_input):
        if not isinstance(content, str):
            continue
        for offset, char in enumerate(content):
            codepoint = ord(char)
            if codepoint in UNICODE_TAG_RANGE:
                return codepoint, offset, "invisible Unicode tag character"
            if codepoint in UNICODE_BIDI_CONTROLS:
                return codepoint, offset, "bidirectional control character"
    return None


def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Check for .env file access (blocks access to sensitive environment files)
        if is_env_file_access(tool_name, tool_input):
            print(
                "BLOCKED: Access to .env files containing sensitive data is prohibited",
                file=sys.stderr,
            )
            print("Use .env.sample for template files instead", file=sys.stderr)
            sys.exit(2)  # Exit code 2 blocks tool call and shows error to Claude

        # Block edits that introduce invisible / visually-spoofed BLOCKER-class
        # unicode (tag characters, bidi controls) into written content. See
        # scripts/validate-unicode-hygiene.py for the canonical codepoint sets and
        # the full MAJOR/MINOR validator used by CI and pre-commit.
        blocker = find_blocker_unicode(tool_name, tool_input)
        if blocker is not None:
            codepoint, offset, label = blocker
            print(
                f"BLOCKED: {label} (U+{codepoint:04X}) in proposed content at offset {offset}",
                file=sys.stderr,
            )
            print(
                "This is a supply-chain hidden-instruction risk. Run "
                "scripts/validate-unicode-hygiene.py to inspect the content.",
                file=sys.stderr,
            )
            sys.exit(2)  # Exit code 2 blocks tool call and shows error to Claude

        # Check for dangerous rm -rf commands
        if tool_name == "Bash":
            command = tool_input.get("command", "")

            # Block rm -rf commands with comprehensive pattern matching
            if is_dangerous_rm_command(command):
                print("BLOCKED: Dangerous rm command detected and prevented", file=sys.stderr)
                sys.exit(2)  # Exit code 2 blocks tool call and shows error to Claude

        # Ensure log directory exists
        log_dir = Path.cwd() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "pre_tool_use.json"

        # Read existing log data or initialize empty list
        if log_path.exists():
            with open(log_path) as f:
                try:
                    log_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    log_data = []
        else:
            log_data = []

        # Append new data
        log_data.append(input_data)

        # Write back to file with formatting
        with open(log_path, "w") as f:
            json.dump(log_data, f, indent=2)

        sys.exit(0)

    except json.JSONDecodeError:
        # Gracefully handle JSON decode errors
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)


if __name__ == "__main__":
    main()
