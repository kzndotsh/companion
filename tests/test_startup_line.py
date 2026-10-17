from __future__ import annotations

import pytest

from companion import daemon
from companion.core.types import RelationshipId


def test_the_startup_line_names_the_persona_the_prefix_and_both_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.delenv("COMPANION_MODEL", raising=False)
    monkeypatch.delenv("COMPANION_SCENE_MODEL", raising=False)
    scene = object()
    line = daemon.startup_line(RelationshipId("telegram-1"), "abcdef0123456789", scene)  # type: ignore[arg-type]
    persona = daemon.PERSONA.removesuffix(".md")
    assert line == (
        f"up as telegram-1 | persona {persona} (prefix abcdef012345)"
        f" | everyday {daemon.openrouter.DEFAULT_MODEL} | scenes {daemon.SCENE_MODEL}"
    )


def test_an_override_and_no_scene_talker_are_shown_as_they_are(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPANION_MODEL", "some/model")
    line = daemon.startup_line(RelationshipId("t"), "a" * 12, None)
    assert "everyday some/model" in line
    assert "scenes the same model" in line
