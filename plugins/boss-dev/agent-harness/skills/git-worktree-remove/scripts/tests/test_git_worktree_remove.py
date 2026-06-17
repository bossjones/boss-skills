"""Tests for git_worktree_remove.py — pure target-resolution helpers."""

from __future__ import annotations

from git_worktree_remove import (
    deletion_flag,
    is_protected,
    resolve_target,
)

WORKTREES = [
    {"path": "/repo", "branch": "main"},
    {"path": "/repo/.claude/worktrees/boss-skills-auth", "branch": "worktree-auth"},
    {"path": "/repo/.claude/worktrees/boss-skills-fix-login", "branch": "worktree-fix-login"},
]


class TestResolveTarget:
    def test_by_full_path(self) -> None:
        target = resolve_target("/repo/.claude/worktrees/boss-skills-auth", WORKTREES)
        assert target is not None
        assert target["branch"] == "worktree-auth"

    def test_by_directory_basename(self) -> None:
        target = resolve_target("boss-skills-auth", WORKTREES)
        assert target is not None
        assert target["branch"] == "worktree-auth"

    def test_by_exact_branch(self) -> None:
        target = resolve_target("worktree-auth", WORKTREES)
        assert target is not None
        assert target["path"].endswith("boss-skills-auth")

    def test_by_bare_name(self) -> None:
        # "auth" resolves to branch "worktree-auth".
        target = resolve_target("auth", WORKTREES)
        assert target is not None
        assert target["branch"] == "worktree-auth"

    def test_unknown_returns_none(self) -> None:
        assert resolve_target("does-not-exist", WORKTREES) is None


class TestIsProtected:
    PROTECTED = ("main", "master", "develop", "staging", "production")

    def test_protected(self) -> None:
        assert is_protected("main", self.PROTECTED) is True

    def test_not_protected(self) -> None:
        assert is_protected("worktree-auth", self.PROTECTED) is False

    def test_none_branch_not_protected(self) -> None:
        assert is_protected(None, self.PROTECTED) is False


class TestDeletionFlag:
    def test_merged_uses_lowercase_d(self) -> None:
        assert deletion_flag(merged=True) == "-d"

    def test_unmerged_uses_uppercase_d(self) -> None:
        assert deletion_flag(merged=False) == "-D"
