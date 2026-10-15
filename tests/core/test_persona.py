from __future__ import annotations

from importlib import resources

import pytest

from companion.core.prompt.prefix import build_prefix

VERSIONS = ["v1.md", "v2.md", "v3.md", "v4.md"]


def _text(name: str) -> str:
    return resources.files("companion.persona").joinpath(name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", VERSIONS)
def test_every_persona_builds_a_valid_prefix(name: str) -> None:
    assert build_prefix(_text(name)).estimated_tokens >= 1024


def test_v3_has_no_example_replies_to_copy() -> None:
    text = _text("v3.md")
    assert "How it should sound" not in text
    assert "They:" not in text
