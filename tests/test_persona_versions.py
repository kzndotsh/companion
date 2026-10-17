"""Every persona version has a file and a changelog entry, dropped ones included."""

from __future__ import annotations

import re
from pathlib import Path

PERSONA = Path(__file__).resolve().parents[1] / "src" / "companion" / "persona"


def _files() -> set[int]:
    return {
        int(m.group(1)) for p in PERSONA.glob("v*.md") if (m := re.fullmatch(r"v(\d+)\.md", p.name))
    }


def _entries() -> set[int]:
    text = (PERSONA / "CHANGELOG.md").read_text(encoding="utf-8")
    return {int(n) for n in re.findall(r"^- \*\*v(\d+)\b", text, re.M)}


def test_every_version_file_has_a_changelog_entry() -> None:
    assert _files() - _entries() == set()


def test_every_changelog_entry_has_its_file_kept_even_if_the_version_was_dropped() -> None:
    assert _entries() - _files() == set()


def test_the_live_persona_is_one_of_the_files() -> None:
    daemon = (PERSONA.parent / "daemon.py").read_text(encoding="utf-8")
    live = re.search(r'^PERSONA = "(v\d+\.md)"', daemon, re.M)
    assert live is not None
    assert (PERSONA / live.group(1)).is_file()
