#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# ///

import json
import sys


def main():
    try:
        # Read JSON input from stdin
        json.load(sys.stdin)

        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Exit cleanly on any other error
        sys.exit(0)


if __name__ == "__main__":
    main()
