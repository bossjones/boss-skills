"""Tests for git_worktree.py — the pure, side-effect-free worktree helpers."""

from __future__ import annotations

from git_worktree import (
    build_branch_name,
    build_worktree_dirname,
    derive_repo_name,
    detect_project_type,
    gitignore_has_worktrees,
    match_worktreeinclude,
    parse_worktreeinclude,
    validate_name,
)

SSH_CONFIG = """\
[core]
\trepositoryformatversion = 0
[remote "origin"]
\turl = git@github.com:bossjones/boss-skills.git
\tfetch = +refs/heads/*:refs/remotes/origin/*
[branch "main"]
\tremote = origin
"""

HTTPS_CONFIG = """\
[remote "origin"]
\turl = https://github.com/bossjones/boss-skills.git
"""

HTTPS_NO_GIT_SUFFIX = """\
[remote "origin"]
\turl = https://github.com/bossjones/boss-skills
"""

MULTI_REMOTE_CONFIG = """\
[remote "upstream"]
\turl = git@github.com:upstream-org/other-repo.git
[remote "origin"]
\turl = git@github.com:bossjones/boss-skills.git
"""

NO_REMOTE_CONFIG = """\
[core]
\trepositoryformatversion = 0
"""


class TestDeriveRepoName:
    def test_ssh_url(self) -> None:
        assert derive_repo_name(SSH_CONFIG, "/tmp/fallback") == "boss-skills"

    def test_https_url(self) -> None:
        assert derive_repo_name(HTTPS_CONFIG, "/tmp/fallback") == "boss-skills"

    def test_https_without_git_suffix(self) -> None:
        assert derive_repo_name(HTTPS_NO_GIT_SUFFIX, "/tmp/fallback") == "boss-skills"

    def test_prefers_origin_over_other_remotes(self) -> None:
        assert derive_repo_name(MULTI_REMOTE_CONFIG, "/tmp/fallback") == "boss-skills"

    def test_falls_back_to_toplevel_basename(self) -> None:
        assert derive_repo_name(NO_REMOTE_CONFIG, "/home/me/my-project") == "my-project"

    def test_falls_back_when_config_empty(self) -> None:
        assert derive_repo_name("", "/home/me/my-project") == "my-project"


class TestBuildWorktreeDirname:
    def test_prefixes_repo_name(self) -> None:
        assert build_worktree_dirname("boss-skills", "auth") == "boss-skills-auth"

    def test_no_double_prefix(self) -> None:
        assert build_worktree_dirname("boss-skills", "boss-skills-auth") == "boss-skills-auth"

    def test_partial_match_is_not_treated_as_prefix(self) -> None:
        # "boss-skills" without the trailing hyphen is not the prefix.
        assert build_worktree_dirname("boss-skills", "boss-skillsauth") == "boss-skills-boss-skillsauth"


class TestBuildBranchName:
    def test_prefixes_worktree(self) -> None:
        assert build_branch_name("auth") == "worktree-auth"

    def test_keeps_slashes(self) -> None:
        assert build_branch_name("fix/login") == "worktree-fix/login"


class TestValidateName:
    def test_accepts_simple_name(self) -> None:
        assert validate_name("auth") is True

    def test_accepts_slashes_underscores_hyphens(self) -> None:
        assert validate_name("fix/login-bug_2") is True

    def test_rejects_empty(self) -> None:
        assert validate_name("") is False

    def test_rejects_spaces(self) -> None:
        assert validate_name("bad name") is False

    def test_rejects_special_chars(self) -> None:
        assert validate_name("bad!name") is False
        assert validate_name("../escape") is False


class TestGitignoreHasWorktrees:
    def test_detects_trailing_slash(self) -> None:
        assert gitignore_has_worktrees(".claude/worktrees/\n*.log\n") is True

    def test_detects_no_trailing_slash(self) -> None:
        assert gitignore_has_worktrees(".claude/worktrees\n") is True

    def test_detects_leading_slash(self) -> None:
        assert gitignore_has_worktrees("/.claude/worktrees/\n") is True

    def test_ignores_comments(self) -> None:
        assert gitignore_has_worktrees("# .claude/worktrees/\n") is False

    def test_absent(self) -> None:
        assert gitignore_has_worktrees("*.log\nnode_modules/\n") is False

    def test_empty(self) -> None:
        assert gitignore_has_worktrees("") is False


class TestParseWorktreeinclude:
    def test_strips_comments_and_blanks(self) -> None:
        text = "# secrets\n.env\n\n.envrc\n  \n# trailing comment\n*.local\n"
        assert parse_worktreeinclude(text) == [".env", ".envrc", "*.local"]

    def test_empty_returns_empty_list(self) -> None:
        assert parse_worktreeinclude("") == []


class TestMatchWorktreeinclude:
    def test_matches_gitignored_files(self) -> None:
        patterns = [".env", ".envrc"]
        gitignored = [".env", ".envrc", "build/output.txt"]
        assert match_worktreeinclude(patterns, gitignored) == [".env", ".envrc"]

    def test_matched_but_not_gitignored_is_skipped(self) -> None:
        # README.md matches the pattern but is NOT gitignored, so it is skipped.
        patterns = ["README.md", ".env"]
        gitignored = [".env"]
        assert match_worktreeinclude(patterns, gitignored) == [".env"]

    def test_glob_star_local(self) -> None:
        patterns = ["*.local"]
        gitignored = ["settings.local", "app.local", "main.py"]
        assert match_worktreeinclude(patterns, gitignored) == ["settings.local", "app.local"]

    def test_double_star_nested(self) -> None:
        patterns = ["**/.claude/settings.local.json"]
        gitignored = ["packages/web/.claude/settings.local.json", "README.md"]
        assert match_worktreeinclude(patterns, gitignored) == ["packages/web/.claude/settings.local.json"]

    def test_no_patterns_returns_empty(self) -> None:
        assert match_worktreeinclude([], [".env"]) == []


class TestDetectProjectType:
    def test_python(self) -> None:
        assert detect_project_type(["pyproject.toml", "README.md"]) == "python"

    def test_node(self) -> None:
        assert detect_project_type(["package.json", "index.js"]) == "node"

    def test_rust(self) -> None:
        assert detect_project_type(["Cargo.toml", "src"]) == "rust"

    def test_go(self) -> None:
        assert detect_project_type(["go.mod"]) == "go"

    def test_generic_when_unknown(self) -> None:
        assert detect_project_type(["Makefile", "README.md"]) == "generic"

    def test_python_wins_when_multiple(self) -> None:
        # Python is first-class for this repo; prefer it on ties.
        assert detect_project_type(["pyproject.toml", "package.json"]) == "python"
