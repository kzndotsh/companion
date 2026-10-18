"""Every persona version has a file and a changelog entry, dropped ones included."""

from __future__ import annotations

import re
from pathlib import Path

from companion import prompts

CHANGELOG = Path(__file__).resolve().parents[1] / "src/companion/prompts/CHANGELOG.md"


def _files() -> set[int]:
    return {int(v.removeprefix("v")) for v in prompts.versions("system/persona")}


def _entries() -> set[int]:
    text = CHANGELOG.read_text(encoding="utf-8")
    return {int(n) for n in re.findall(r"^- \*\*system/persona v(\d+)\*\*", text, re.M)}


def test_every_version_file_has_a_changelog_entry() -> None:
    assert _files() - _entries() == set()


def test_every_changelog_entry_has_its_file_kept_even_if_the_version_was_dropped() -> None:
    assert _entries() - _files() == set()


def test_the_live_persona_is_one_of_the_files() -> None:
    assert prompts.manifest()["system/persona"] in prompts.versions("system/persona")
