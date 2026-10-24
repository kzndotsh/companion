"""Every feature folder keeps one README in the same shape, naming every file and prompt it has, so
a reader finds the same things in the same place (2026-10-24)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FEATURES = Path("src/companion/features")
SECTIONS = ("## How it works", "## Files", "## Prompts", "## Commands", "## Measured", "## Tests")
_VERSIONED = re.compile(r"`(?:system|notes|messages)/[a-z0-9-]+(?:`\s*\(v\d+\)|@v\d+`)")
_PROMPT = re.compile(r"""get\(\s*f?["']((?:system|notes|messages)/[a-z0-9-]+)["']""")
NAMES = sorted(p.parent.name for p in FEATURES.glob("*/__init__.py"))


def _readme(name: str) -> str:
    return (FEATURES / name / "README.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", NAMES)
def test_the_readme_has_the_standard_sections_in_order(name: str) -> None:
    text = _readme(name)
    assert text.startswith("# "), f"{name}: starts with its title"
    assert "**Status:**" in text, f"{name}: has a status line"
    at = [text.find(s + "\n") for s in SECTIONS]
    assert all(i >= 0 for i in at), (
        f"{name}: missing {[s for s, i in zip(SECTIONS, at, strict=True) if i < 0]}"
    )
    assert at == sorted(at), f"{name}: sections out of order"


@pytest.mark.parametrize("name", NAMES)
def test_the_readme_names_every_file_and_prompt_the_feature_has(name: str) -> None:
    text = _readme(name)
    folder = FEATURES / name
    files = sorted(
        p.name
        for p in folder.iterdir()
        if p.is_file() and not p.name.startswith("__") and p.name != "README.md"
    )
    assert not [f for f in files if f"`{f}`" not in text], f"{name}: files not in its README"
    used = {m for p in folder.glob("*.py") for m in _PROMPT.findall(p.read_text(encoding="utf-8"))}
    assert not [u for u in sorted(used) if f"`{u}`" not in text], (
        f"{name}: prompts not in its README"
    )
    assert f"`tests/features/{name}/`" in text, f"{name}: points at its tests"


@pytest.mark.parametrize("name", NAMES)
def test_the_readme_names_prompts_without_their_version(name: str) -> None:
    """The manifest holds the current versions (`companion prompts`); a version here goes stale."""
    assert not _VERSIONED.findall(_readme(name)), f"{name}: a prompt is named with its version"
