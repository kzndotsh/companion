from __future__ import annotations

from importlib import resources

import pytest

from companion.core.prompt.prefix import build_prefix

VERSIONS = ["v1.md", "v2.md", "v3.md", "v4.md", "v5.md", "v6.md", "v7.md", "v8.md", "v9.md"]


def _text(name: str) -> str:
    return resources.files("companion.persona").joinpath(name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", VERSIONS)
def test_every_persona_builds_a_valid_prefix(name: str) -> None:
    assert build_prefix(_text(name)).estimated_tokens >= 1024


def test_v3_has_no_example_replies_to_copy() -> None:
    text = _text("v3.md")
    assert "How it should sound" not in text
    assert "They:" not in text


def test_v5_tells_the_companion_who_the_companion_is() -> None:
    text = _text("v5.md")
    assert '"the companion" is you' in text


def test_v6_has_a_first_person_rule() -> None:
    assert 'never "the companion"' in _text("v6.md")


def test_v9_keeps_the_rules_the_replays_showed_it_needs() -> None:
    text = _text("v9.md")
    assert "## Claims you cannot judge" in text
    assert "## Praise" in text
    assert 'say "working on me"' in text
    assert "Do not claim to feel, sense or watch things you cannot observe" in text
