#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# ///

from __future__ import annotations

import json
import re
import sys
from collections.abc import Generator
from typing import Any

# Matches `rm` only where it is the command actually being executed: at the
# start of the command line or of a chained sub-command (after a shell separator
# `\n ; & | ` "`" ` (`), optionally via `sudo`/`command` or a leading `\` used to
# bypass an alias. This deliberately ignores `rm` when it is a flag (`--rm`, the
# `-` prevents a match) or another program's subcommand argument (`docker rm`,
# `git rm`), which are not the destructive `/bin/rm`.
_RM_INVOCATION = re.compile(r"(?:^|[\n;&|`(])\s*(?:sudo\s+)?(?:command\s+)?\\?rm\b")

# Recursive+force flag combinations, in any order.
_RM_FORCE_RECURSIVE = [
    r"-[a-z]*r[a-z]*f",  # -rf, -Rf, -rvf, ...
    r"-[a-z]*f[a-z]*r",  # -fr variations
    r"--recursive\b.*--force\b",  # --recursive --force
    r"--force\b.*--recursive\b",  # --force --recursive
    r"-r\b.*-f\b",  # -r ... -f
    r"-f\b.*-r\b",  # -f ... -r
]

# Dangerous targets for a recursive rm. Each matches the target as a whole
# argument so ordinary relative paths (e.g. "rm -r ./build/output") are safe.
_RM_DANGEROUS_PATHS = [
    r"\s/\s*$",  # rm -rf /            (root)
    r"\s/\s+",  # rm -rf / home/user  (root as a separate argument)
    r"\s/\*",  # rm -rf /*            (everything under root)
    r"\s~\s*$",  # rm -rf ~            (home directory)
    r"\s~/",  # rm -rf ~/...         (home subtree)
    r"\$home\b",  # rm -rf $HOME         (home env var; segment is lowercased)
    r"\.\.",  # parent-directory references (.. , ../..)
    r"\s\*\s*$",  # rm -rf *             (bare wildcard)
    r"\s\./?\s*$",  # rm -rf . or ./       (current directory)
]


def is_dangerous_rm_command(command):
    """
    Comprehensive detection of dangerous rm commands.

    Only flags ``rm`` when it is the command actually being invoked (command
    position), then inspects that invocation's arguments for destructive
    recursive/force patterns or dangerous targets. ``rm`` appearing as a flag
    (``--rm``) or another tool's subcommand (``docker rm``, ``git rm``) is not
    treated as the destructive ``/bin/rm``.
    """
    # Lowercase and collapse intra-line whitespace, but KEEP newlines: each line
    # is its own command, so a bare `rm` on its own line must stay detectable.
    normalized = "\n".join(" ".join(line.split()) for line in command.lower().splitlines())

    for match in _RM_INVOCATION.finditer(normalized):
        # Arguments to this rm invocation, up to the next shell separator.
        rest = normalized[match.end() :]
        segment = re.split(r"[\n;&|`)]", rest, maxsplit=1)[0]

        if any(re.search(pattern, segment) for pattern in _RM_FORCE_RECURSIVE):
            return True

        if re.search(r"-[a-z]*r", segment):  # recursive flag present
            if any(re.search(path, segment) for path in _RM_DANGEROUS_PATHS):
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
            # Passing the file to a subprocess via `--env-file <path>` /
            # `--env-file=<path>` does not surface its contents to the model, so
            # strip those usages before scanning.
            command = re.sub(r"--env-file(?:=|\s+)\S+", " ", command)

            # Block any reference to a real secret env file (e.g. "source .env",
            # "cat .envrc", "less .env.local") while allowing the secret-free
            # committed templates (.env.sample / .env.example) and unrelated
            # files like `config.env`. The leading `(?<![\w.])` lookbehind keeps
            # `config.env` (preceded by a word char) from matching.
            env_patterns = [
                r"(?<![\w.])\.envrc\b",  # direnv secrets
                r"(?<![\w.])\.env(?![\w.])",  # bare .env
                r"(?<![\w.])\.env\.(?!sample\b)(?!example\b)[\w.-]+",  # .env.local etc.
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


def _iter_edit_content(tool_name: str, tool_input: dict[str, Any]) -> Generator[str, None, None]:
    """Yield each chunk of proposed content for a Write/Edit/MultiEdit call."""
    if tool_name == "Write":
        yield tool_input.get("content", "")
    elif tool_name == "Edit":
        yield tool_input.get("new_string", "")
    elif tool_name == "MultiEdit":
        for edit in tool_input.get("edits", []) or []:
            yield edit.get("new_string", "")


def find_blocker_unicode(tool_name: str, tool_input: dict[str, Any]) -> tuple[int, int, str] | None:
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

        sys.exit(0)

    except json.JSONDecodeError:
        # Gracefully handle JSON decode errors
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)


if __name__ == "__main__":
    main()
