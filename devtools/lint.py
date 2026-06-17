import subprocess

from funlog import log_calls
from rich import get_console, reconfigure
from rich import print as rprint

# Update as needed.
SRC_PATHS = ["devtools", "scripts", "plugins"]
DOC_PATHS = ["README.md"]
# Type-checked paths (kept narrower than SRC_PATHS while plugins are scaffolding).
# Add plugin subdirectories here as they exit scaffolding and gain type annotations.
# The agent-harness skill scripts below are fully annotated PEP 723 scripts; their
# test directories use sys.path shims and stay excluded via pyrightconfig.json.
_AGENT_HARNESS_SKILLS = "plugins/boss-dev/agent-harness/skills"
TYPE_CHECK_PATHS = [
    "devtools",
    "scripts",
    f"{_AGENT_HARNESS_SKILLS}/fetch-diff/scripts/fetch_diff.py",
    f"{_AGENT_HARNESS_SKILLS}/fetch-unresolved-comments/scripts/fetch_unresolved_comments.py",
    f"{_AGENT_HARNESS_SKILLS}/pr-review/scripts/validate_review.py",
    f"{_AGENT_HARNESS_SKILLS}/git-worktree/scripts/git_worktree.py",
    f"{_AGENT_HARNESS_SKILLS}/git-worktree-status/scripts/git_worktree_status.py",
    f"{_AGENT_HARNESS_SKILLS}/git-worktree-clean/scripts/git_worktree_clean.py",
    f"{_AGENT_HARNESS_SKILLS}/git-worktree-remove/scripts/git_worktree_remove.py",
    f"{_AGENT_HARNESS_SKILLS}/worktree-doctor/scripts/worktree_doctor.py",
]


reconfigure(emoji=not get_console().options.legacy_windows)  # No emojis on legacy windows.


def main():
    rprint()

    errcount = 0
    errcount += run(["codespell", "--write-changes", *SRC_PATHS, *DOC_PATHS])
    errcount += run(["ruff", "check", "--fix", *SRC_PATHS])
    errcount += run(["ruff", "format", *SRC_PATHS])
    errcount += run(["basedpyright", "--stats", *TYPE_CHECK_PATHS])

    rprint()

    if errcount != 0:
        rprint(f"[bold red]:x: Lint failed with {errcount} errors.[/bold red]")
    else:
        rprint("[bold green]:white_check_mark: Lint passed![/bold green]")
    rprint()

    return errcount


@log_calls(level="warning", show_timing_only=True)
def run(cmd: list[str]) -> int:
    rprint()
    rprint(f"[bold green]>> {' '.join(cmd)}[/bold green]")
    errcount = 0
    try:
        subprocess.run(cmd, text=True, check=True)  # noqa: S603
    except KeyboardInterrupt:
        rprint("[yellow]Keyboard interrupt - Cancelled[/yellow]")
        errcount = 1
    except subprocess.CalledProcessError as e:
        rprint(f"[bold red]Error: {e}[/bold red]")
        errcount = 1

    return errcount


if __name__ == "__main__":
    exit(main())
