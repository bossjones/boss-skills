"""Tests for worktree_doctor.py — pure scan/detect/suggest helpers."""

from __future__ import annotations

from worktree_doctor import (
    DEFAULT_CANDIDATE_PATTERNS,
    build_worktreeinclude_suggestion,
    detect_project_types,
    gitignore_has_worktrees,
    scan_gitignored_candidates,
)


class TestScanGitignoredCandidates:
    def test_matches_env_and_local_files(self) -> None:
        gitignored = [".env", ".env.local", ".envrc", "app.local", "main.py", "build/out.o"]
        found = scan_gitignored_candidates(gitignored, DEFAULT_CANDIDATE_PATTERNS)
        assert ".env" in found
        assert ".env.local" in found
        assert ".envrc" in found
        assert "app.local" in found
        assert "main.py" not in found
        assert "build/out.o" not in found

    def test_matches_nested_local_config(self) -> None:
        gitignored = ["packages/web/.claude/settings.local.json", "README.md"]
        found = scan_gitignored_candidates(gitignored, DEFAULT_CANDIDATE_PATTERNS)
        assert "packages/web/.claude/settings.local.json" in found

    def test_matches_secrets(self) -> None:
        gitignored = ["secrets.yaml", "secrets/token.txt", "config.py"]
        found = scan_gitignored_candidates(gitignored, DEFAULT_CANDIDATE_PATTERNS)
        assert "secrets.yaml" in found

    def test_no_matches(self) -> None:
        assert scan_gitignored_candidates(["a.py", "b.txt"], DEFAULT_CANDIDATE_PATTERNS) == []

    def test_deduplicates_and_preserves_order(self) -> None:
        found = scan_gitignored_candidates([".env", ".env", ".envrc"], DEFAULT_CANDIDATE_PATTERNS)
        assert found == [".env", ".envrc"]

    def test_excludes_vendored_paths(self) -> None:
        gitignored = [
            ".env",
            ".venv/lib/python3.13/site-packages/secrets.py",
            "node_modules/pkg/config.local",
        ]
        found = scan_gitignored_candidates(gitignored, DEFAULT_CANDIDATE_PATTERNS)
        assert found == [".env"]


class TestDetectProjectTypes:
    def test_single(self) -> None:
        assert detect_project_types(["pyproject.toml", "README.md"]) == ["python"]

    def test_multiple_in_canonical_order(self) -> None:
        files = ["go.mod", "package.json", "pyproject.toml", "Cargo.toml"]
        assert detect_project_types(files) == ["python", "node", "rust", "go"]

    def test_none(self) -> None:
        assert detect_project_types(["Makefile"]) == []


class TestBuildWorktreeincludeSuggestion:
    def test_includes_candidate_lines(self) -> None:
        text = build_worktreeinclude_suggestion([".env", ".envrc"])
        assert ".env" in text
        assert ".envrc" in text
        # Header comment present.
        assert text.lstrip().startswith("#")

    def test_empty_suggests_common_defaults(self) -> None:
        text = build_worktreeinclude_suggestion([])
        assert ".env" in text
        assert ".envrc" in text


class TestGitignoreHasWorktrees:
    def test_present(self) -> None:
        assert gitignore_has_worktrees(".claude/worktrees/\n") is True

    def test_absent(self) -> None:
        assert gitignore_has_worktrees("*.log\n") is False
