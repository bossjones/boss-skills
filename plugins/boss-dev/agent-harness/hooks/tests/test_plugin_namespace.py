"""Focused tests for the plugin-repository namespace used by harness artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest
from hook_loader import HOOKS_DIR, load_hook

plugin_namespace = load_hook("utils/plugin_namespace.py")


def _make_marketplace(root: Path) -> Path:
    """Create a marketplace repository root and return it."""
    manifest = root / ".claude-plugin" / "marketplace.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}", encoding="utf-8")
    return root


def _make_plugin_tree(marketplace_root: Path) -> Path:
    """Create the plugin layout below a marketplace root and return the hooks dir."""
    plugin_root = marketplace_root / "plugins" / "boss-dev" / "agent-harness"
    manifest = plugin_root / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}", encoding="utf-8")
    hooks_dir = plugin_root / "hooks" / "utils"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    return hooks_dir


def test_nearest_marketplace_ancestor_names_the_namespace(tmp_path: Path) -> None:
    marketplace = _make_marketplace(tmp_path / "boss-skills")
    hooks_dir = _make_plugin_tree(marketplace)

    name, source = plugin_namespace.namespace_from(hooks_dir / "plugin_namespace.py")

    assert name == "boss-skills"
    assert source == marketplace


def test_plugin_manifest_without_marketplace_manifest_is_skipped(tmp_path: Path) -> None:
    """The plugin's own .claude-plugin/ holds plugin.json only and must not stop the walk."""
    marketplace = _make_marketplace(tmp_path / "aif-skills")
    hooks_dir = _make_plugin_tree(marketplace)
    plugin_root = hooks_dir.parent.parent

    assert (plugin_root / ".claude-plugin" / "plugin.json").is_file()
    assert not (plugin_root / ".claude-plugin" / "marketplace.json").exists()
    assert plugin_namespace.namespace_from(hooks_dir / "plugin_namespace.py") == ("aif-skills", marketplace)


def test_nested_marketplaces_resolve_to_the_nearest_ancestor(tmp_path: Path) -> None:
    outer = _make_marketplace(tmp_path / "outer-marketplace")
    inner = _make_marketplace(outer / "vendored" / "inner-marketplace")
    hooks_dir = _make_plugin_tree(inner)

    name, source = plugin_namespace.namespace_from(hooks_dir / "plugin_namespace.py")

    assert name == "inner-marketplace"
    assert source == inner


def test_missing_marketplace_manifest_falls_back_to_the_default_namespace(tmp_path: Path) -> None:
    """A tree vendored into a foreign repo has no marketplace manifest above it."""
    hooks_dir = tmp_path / "vendored" / ".claude" / "hooks" / "utils"
    hooks_dir.mkdir(parents=True)

    assert plugin_namespace.namespace_from(hooks_dir / "plugin_namespace.py") == (
        plugin_namespace.DEFAULT_NAMESPACE,
        None,
    )


def test_global_cache_path_uses_the_marketplace_segment_without_a_manifest(tmp_path: Path) -> None:
    """Claude's cache keeps the marketplace name in its path, not a manifest."""
    module_path = (
        tmp_path / ".claude" / "plugins" / "cache" / "boss-skills" / "agent-harness" / "0.31.0" / "hooks" / "utils"
    )
    module_path.mkdir(parents=True)

    assert plugin_namespace.namespace_from(module_path / "plugin_namespace.py") == ("boss-skills", None)


@pytest.mark.parametrize(
    ("directory_name", "expected"),
    [
        ("boss-skills", "boss-skills"),
        ("My Repo (v2)", "my-repo-v2"),
        (".dotted", "dotted"),
        ("UPPER", "upper"),
        ("---", "agent-harness"),
        ("日本語", "agent-harness"),
    ],
)
def test_marketplace_directory_names_are_slugged(directory_name: str, expected: str, tmp_path: Path) -> None:
    marketplace = _make_marketplace(tmp_path / directory_name)
    hooks_dir = _make_plugin_tree(marketplace)

    assert plugin_namespace.namespace_from(hooks_dir / "plugin_namespace.py")[0] == expected


def test_slug_falls_back_when_nothing_survives_normalization() -> None:
    assert plugin_namespace.slug("") == plugin_namespace.DEFAULT_NAMESPACE
    assert plugin_namespace.slug("...") == plugin_namespace.DEFAULT_NAMESPACE


def test_installed_namespace_matches_this_checkouts_marketplace_root() -> None:
    """Assert against the real tree without hardcoding this repository's name."""
    module_path = (HOOKS_DIR / "utils" / "plugin_namespace.py").resolve()
    expected_name, expected_source = plugin_namespace.namespace_from(module_path)

    assert expected_source is not None
    assert (expected_source / ".claude-plugin" / "marketplace.json").is_file()
    assert plugin_namespace.plugin_namespace() == expected_name
    assert expected_name == plugin_namespace.slug(expected_source.name)


def test_plugin_namespace_is_cached_across_calls() -> None:
    plugin_namespace.plugin_namespace.cache_clear()
    first = plugin_namespace.plugin_namespace()

    assert plugin_namespace.plugin_namespace() is first
    assert plugin_namespace.plugin_namespace.cache_info().hits >= 1
