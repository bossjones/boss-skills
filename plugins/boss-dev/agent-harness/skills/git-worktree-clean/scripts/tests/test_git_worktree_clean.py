"""Tests for git_worktree_clean.py — pure parsing/classification helpers."""

from __future__ import annotations

from git_worktree_clean import (
    classify_worktree,
    format_size,
    parse_worktree_list_porcelain,
)

PORCELAIN = """\
worktree /home/me/boss-skills
HEAD 1111111111111111111111111111111111111111
branch refs/heads/main

worktree /home/me/boss-skills/.claude/worktrees/boss-skills-auth
HEAD 2222222222222222222222222222222222222222
branch refs/heads/worktree-auth

worktree /home/me/boss-skills/.claude/worktrees/boss-skills-detached
HEAD 3333333333333333333333333333333333333333
detached
"""


class TestParseWorktreeListPorcelain:
    def test_parses_all_entries(self) -> None:
        entries = parse_worktree_list_porcelain(PORCELAIN)
        assert len(entries) == 3

    def test_first_entry_is_main(self) -> None:
        entries = parse_worktree_list_porcelain(PORCELAIN)
        assert entries[0]["path"] == "/home/me/boss-skills"
        assert entries[0]["branch"] == "main"
        assert entries[0]["is_main"] is True

    def test_strips_refs_heads_prefix(self) -> None:
        entries = parse_worktree_list_porcelain(PORCELAIN)
        assert entries[1]["branch"] == "worktree-auth"
        assert entries[1]["is_main"] is False

    def test_detached_head_has_no_branch(self) -> None:
        entries = parse_worktree_list_porcelain(PORCELAIN)
        assert entries[2]["branch"] is None
        assert entries[2]["detached"] is True

    def test_captures_head_sha(self) -> None:
        entries = parse_worktree_list_porcelain(PORCELAIN)
        assert entries[1]["head"] == "2" * 40

    def test_empty_input(self) -> None:
        assert parse_worktree_list_porcelain("") == []


class TestClassifyWorktree:
    PROTECTED = ("main", "master", "develop", "staging", "production")

    def test_protected_branch(self) -> None:
        assert classify_worktree("develop", False, self.PROTECTED) == "protected"

    def test_merged_branch(self) -> None:
        assert classify_worktree("worktree-auth", True, self.PROTECTED) == "merged"

    def test_unmerged_branch(self) -> None:
        assert classify_worktree("worktree-auth", False, self.PROTECTED) == "unmerged"

    def test_detached_is_unmerged(self) -> None:
        assert classify_worktree(None, False, self.PROTECTED) == "unmerged"

    def test_protected_takes_priority_over_merge_state(self) -> None:
        assert classify_worktree("main", True, self.PROTECTED) == "protected"


class TestFormatSize:
    def test_bytes(self) -> None:
        assert format_size(512) == "512 B"

    def test_kilobytes(self) -> None:
        assert format_size(2048) == "2.0 KB"

    def test_megabytes(self) -> None:
        assert format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_zero(self) -> None:
        assert format_size(0) == "0 B"
