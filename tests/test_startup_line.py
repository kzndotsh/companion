from __future__ import annotations

import pytest

from companion import daemon, prompts
from companion.characters import parse
from companion.core.types import RelationshipId
from companion.settings import ROLEPLAY_MODEL


@pytest.fixture(autouse=True)
def _no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without OpenRouter there is no talker fallback; the first test sets a key and shows one."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("COMPANION_TALKER_FALLBACK", raising=False)
    monkeypatch.delenv("COMPANION_CONSOLIDATE", raising=False)
    monkeypatch.delenv("COMPANION_ROLEPLAY_MODEL", raising=False)


def test_the_startup_line_names_the_persona_the_prefix_and_both_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.delenv("COMPANION_MODEL", raising=False)
    monkeypatch.delenv("COMPANION_ROLEPLAY_MODEL", raising=False)
    monkeypatch.delenv("COMPANION_DAILY_CAP_USD", raising=False)
    monkeypatch.delenv("COMPANION_PACE", raising=False)
    monkeypatch.delenv("COMPANION_SPLIT", raising=False)
    monkeypatch.delenv("COMPANION_INITIATIVE", raising=False)
    monkeypatch.delenv("COMPANION_LISTEN", raising=False)
    monkeypatch.delenv("COMPANION_MOOD", raising=False)
    monkeypatch.delenv("COMPANION_RESAMPLE", raising=False)
    monkeypatch.delenv("COMPANION_ROUTE_INTIMATE", raising=False)
    line = daemon.startup_line(RelationshipId("telegram-1"), "abcdef0123456789")
    persona = prompts.get("system/persona").version
    assert line == (
        f"up as telegram-1 | persona {persona} (prefix abcdef012345) | character none"
        f" | prompts {prompts.set_hash()}"
        f" | everyday {daemon.openrouter.DEFAULT_MODEL} | roleplay {ROLEPLAY_MODEL}"
        " | daily cap $10.00 | pace natural | split on | listen on | initiative shadow"
        " | mood shadow | resample on | intimate stays"
        " | relevance on | talker fallback deepseek/deepseek-v4.1-flash | memory check shadow"
        " | promises shadow | lore on | reminders on"
    )


def test_the_pace_setting_is_shown_and_an_unknown_one_means_natural(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPANION_PACE", "slow")
    assert " | pace slow" in daemon.startup_line(RelationshipId("t"), "a" * 12)
    monkeypatch.setenv("COMPANION_PACE", "warp")
    assert " | pace natural" in daemon.startup_line(RelationshipId("t"), "a" * 12)


def test_the_split_setting_is_shown_and_off_turns_it_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANION_SPLIT", "off")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        "split off | listen on | initiative shadow | mood shadow | resample on | intimate stays"
        " | relevance on | talker fallback off | memory check shadow"
        " | promises shadow | lore on | reminders on"
    )
    monkeypatch.setenv("COMPANION_SPLIT", "on")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        "split on | listen on | initiative shadow | mood shadow | resample on | intimate stays"
        " | relevance on | talker fallback off | memory check shadow"
        " | promises shadow | lore on | reminders on"
    )


def test_an_override_and_no_roleplay_talker_are_shown_as_they_are(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPANION_MODEL", "some/model")
    line = daemon.startup_line(RelationshipId("t"), "a" * 12)
    assert "everyday some/model" in line
    assert "roleplay the same model" in line


def test_the_initiative_mode_is_shadow_unless_turned_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COMPANION_MOOD", raising=False)
    monkeypatch.delenv("COMPANION_INITIATIVE", raising=False)
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        "initiative shadow | mood shadow | resample on | intimate stays"
        " | relevance on | talker fallback off | memory check shadow"
        " | promises shadow | lore on | reminders on"
    )
    monkeypatch.setenv("COMPANION_INITIATIVE", "off")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        "initiative off | mood shadow | resample on | intimate stays"
        " | relevance on | talker fallback off | memory check shadow"
        " | promises shadow | lore on | reminders on"
    )
    monkeypatch.setenv("COMPANION_INITIATIVE", "live")  # there is no live mode yet
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        "initiative shadow | mood shadow | resample on | intimate stays"
        " | relevance on | talker fallback off | memory check shadow"
        " | promises shadow | lore on | reminders on"
    )


def test_listen_is_on_unless_turned_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANION_LISTEN", "off")
    assert " | listen off | " in daemon.startup_line(RelationshipId("t"), "a" * 12)
    monkeypatch.setenv("COMPANION_LISTEN", "on")
    assert " | listen on | " in daemon.startup_line(RelationshipId("t"), "a" * 12)


def test_the_startup_line_names_the_character() -> None:
    mika = parse("You are Mika. Bubbly.\n", "mika", "local")
    line = daemon.startup_line(RelationshipId("t"), "a" * 12, mika)
    assert " | character mika@local | " in line


@pytest.mark.parametrize(
    ("raw", "shown"), [("", "shadow"), ("on", "on"), ("off", "off"), ("x", "shadow")]
)
def test_the_mood_is_shadow_unless_set_on_or_off(
    monkeypatch: pytest.MonkeyPatch, raw: str, shown: str
) -> None:
    monkeypatch.setenv("COMPANION_MOOD", raw)
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        f"mood {shown} | resample on | intimate stays"
        " | relevance on | talker fallback off | memory check shadow"
        " | promises shadow | lore on | reminders on"
    )


def test_resample_is_on_unless_turned_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANION_RESAMPLE", "off")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        "resample off | intimate stays"
        " | relevance on | talker fallback off | memory check shadow"
        " | promises shadow | lore on | reminders on"
    )
    monkeypatch.delenv("COMPANION_RESAMPLE")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        "resample on | intimate stays"
        " | relevance on | talker fallback off | memory check shadow"
        " | promises shadow | lore on | reminders on"
    )


def test_intimate_talk_stays_unless_routing_is_turned_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANION_ROUTE_INTIMATE", "on")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        "intimate may route | relevance on | talker fallback off | memory check shadow"
        " | promises shadow | lore on | reminders on"
    )
    monkeypatch.setenv("COMPANION_ROUTE_INTIMATE", "off")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        "intimate stays | relevance on | talker fallback off | memory check shadow"
        " | promises shadow | lore on | reminders on"
    )


def test_the_relevance_look_up_is_on_unless_shadow_or_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANION_RELEVANCE", "off")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        "relevance off | talker fallback off | memory check shadow | promises shadow"
        " | lore on | reminders on"
    )


def test_the_promise_read_is_shadow_unless_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANION_PROMISES", "off")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        "| promises off | lore on | reminders on"
    )
    monkeypatch.setenv("COMPANION_PROMISES", "on")  # nothing live yet, so on reads as shadow
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
        "| promises shadow | lore on | reminders on"
    )


def test_the_lore_note_is_on_unless_shadow_or_off(monkeypatch: pytest.MonkeyPatch) -> None:
    for raw, shown in (("shadow", "shadow"), ("off", "off"), ("x", "on")):
        monkeypatch.setenv("COMPANION_LORE", raw)
        assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith(
            f"| lore {shown} | reminders on"
        )


def test_reminders_are_on_unless_turned_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANION_REMINDERS", "off")
    assert daemon.startup_line(RelationshipId("t"), "a" * 12).endswith("| reminders off")
