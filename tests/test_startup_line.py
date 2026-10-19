from __future__ import annotations

import pytest

from companion import daemon, prompts
from companion.characters import parse
from companion.core.types import RelationshipId


def test_the_startup_line_names_the_persona_the_prefix_and_both_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.delenv("COMPANION_MODEL", raising=False)
    monkeypatch.delenv("COMPANION_SCENE_MODEL", raising=False)
    monkeypatch.delenv("COMPANION_DAILY_CAP_USD", raising=False)
    monkeypatch.delenv("COMPANION_PACE", raising=False)
    monkeypatch.delenv("COMPANION_SPLIT", raising=False)
    monkeypatch.delenv("COMPANION_INITIATIVE", raising=False)
    monkeypatch.delenv("COMPANION_LISTEN", raising=False)
    monkeypatch.delenv("COMPANION_MOOD", raising=False)
    scene = object()
    line = daemon.startup_line(RelationshipId("telegram-1"), "abcdef0123456789", scene)  # type: ignore[arg-type]
    persona = prompts.get("system/persona").version
    assert line == (
        f"up as telegram-1 | persona {persona} (prefix abcdef012345) | character none"
        f" | prompts {prompts.set_hash()}"
        f" | everyday {daemon.openrouter.DEFAULT_MODEL} | scenes {daemon.SCENE_MODEL}"
        " | daily cap $10.00 | pace natural | split on | listen on | initiative shadow"
        " | mood shadow"
    )


def test_the_pace_setting_is_shown_and_an_unknown_one_means_natural(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPANION_PACE", "slow")
    assert " | pace slow" in daemon.startup_line(RelationshipId("t"), "a" * 12, None)
    monkeypatch.setenv("COMPANION_PACE", "warp")
    assert " | pace natural" in daemon.startup_line(RelationshipId("t"), "a" * 12, None)


def test_the_split_setting_is_shown_and_off_turns_it_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANION_SPLIT", "off")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12, None).endswith(
        "split off | listen on | initiative shadow | mood shadow"
    )
    monkeypatch.setenv("COMPANION_SPLIT", "on")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12, None).endswith(
        "split on | listen on | initiative shadow | mood shadow"
    )


def test_an_override_and_no_scene_talker_are_shown_as_they_are(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPANION_MODEL", "some/model")
    line = daemon.startup_line(RelationshipId("t"), "a" * 12, None)
    assert "everyday some/model" in line
    assert "scenes the same model" in line


def test_the_initiative_mode_is_shadow_unless_turned_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COMPANION_MOOD", raising=False)
    monkeypatch.delenv("COMPANION_INITIATIVE", raising=False)
    assert daemon.startup_line(RelationshipId("t"), "a" * 12, None).endswith(
        "initiative shadow | mood shadow"
    )
    monkeypatch.setenv("COMPANION_INITIATIVE", "off")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12, None).endswith(
        "initiative off | mood shadow"
    )
    monkeypatch.setenv("COMPANION_INITIATIVE", "live")  # there is no live mode yet
    assert daemon.startup_line(RelationshipId("t"), "a" * 12, None).endswith(
        "initiative shadow | mood shadow"
    )


def test_listen_is_on_unless_turned_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANION_LISTEN", "off")
    assert " | listen off | " in daemon.startup_line(RelationshipId("t"), "a" * 12, None)
    monkeypatch.setenv("COMPANION_LISTEN", "on")
    assert " | listen on | " in daemon.startup_line(RelationshipId("t"), "a" * 12, None)


def test_the_startup_line_names_the_character() -> None:
    mika = parse("You are Mika. Bubbly.\n", "mika", "local")
    line = daemon.startup_line(RelationshipId("t"), "a" * 12, None, mika)
    assert " | character mika@local | " in line


@pytest.mark.parametrize(
    ("raw", "shown"), [("", "shadow"), ("on", "on"), ("off", "off"), ("x", "shadow")]
)
def test_the_mood_is_shadow_unless_set_on_or_off(
    monkeypatch: pytest.MonkeyPatch, raw: str, shown: str
) -> None:
    monkeypatch.setenv("COMPANION_MOOD", raw)
    assert daemon.startup_line(RelationshipId("t"), "a" * 12, None).endswith(f"mood {shown}")
