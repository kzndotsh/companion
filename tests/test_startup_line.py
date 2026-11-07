from __future__ import annotations

import pytest

from companion import prompts, startup
from companion.characters import parse
from companion.core.switch import SWITCHES
from companion.core.types import RelationshipId
from companion.models import openrouter
from companion.settings import JUDGE_MODEL, ROLEPLAY_MODEL


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every switch at its default and no OpenRouter key, unless a test sets one."""
    for s in SWITCHES:
        monkeypatch.delenv(s.env, raising=False)
    for name in (
        "OPENROUTER_API_KEY",
        "COMPANION_EVERYDAY_MODEL",
        "COMPANION_EVERYDAY_STANDBY",
        "COMPANION_ROLEPLAY_MODEL",
        "COMPANION_JUDGE_MODEL",
        "COMPANION_JUDGE_ROUTES",
        "COMPANION_DAILY_CAP_USD",
        "COMPANION_PACE",
    ):
        monkeypatch.delenv(name, raising=False)


def _lines(character: str | None = None) -> list[str]:
    char = parse(f"You are {character}.\n", character, "local") if character else None
    return startup.startup_lines(RelationshipId("t"), "abcdef0123456789", char)


def _row(label: str) -> list[str]:
    """A row's items, its wrapped lines joined."""
    lines = _lines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"  {label} "))
    text = lines[start][11:]
    for line in lines[start + 1 :]:
        if not line.startswith(" " * 11):
            break
        text += " " + line.strip()
    return [item.strip() for item in text.split(",")]


def test_the_startup_block_with_every_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    persona = prompts.get("system/persona").version
    assert _lines() == [
        "up as t on telegram",
        (
            f"  prompts  persona {persona} (prefix abcdef012345), character none,"
            f" set {prompts.set_hash()}"
        ),
        f"  everyday {openrouter.DEFAULT_MODEL}, standby {ROLEPLAY_MODEL}",
        f"  roleplay {ROLEPLAY_MODEL}",
        f"  judges   {JUDGE_MODEL} (crisis on deepseek/deepseek-v4.1-flash)",
        "  limits   daily cap $10.00, pace natural",
        (
            "  live     split, listen, mood, redraw, relevance, re-read, lore, focus, reminders,"
            " episodes,"
        ),
        "           own marks, crisis, calendar, intimate memory",
        "  shadow   initiative, promises, now, history",
        "  off      none",
        "  dials    intimate stays, hedged plans loose, reach warm",
    ]


@pytest.mark.parametrize(
    ("env", "label", "raw", "row"),
    [
        ("COMPANION_SPLIT", "split", "off", "off"),
        ("COMPANION_LISTEN", "listen", "off", "off"),
        ("COMPANION_INITIATIVE", "initiative", "off", "off"),
        ("COMPANION_INITIATIVE", "initiative", "on", "shadow"),  # no live position yet
        ("COMPANION_MOOD", "mood", "shadow", "shadow"),
        ("COMPANION_MOOD", "mood", "yes", "live"),
        ("COMPANION_REDRAW", "redraw", "off", "off"),
        ("COMPANION_RELEVANCE", "relevance", "off", "off"),
        ("COMPANION_PROMISES", "promises", "on", "shadow"),  # nothing live yet
        ("COMPANION_LORE", "lore", "shadow", "shadow"),
        ("COMPANION_REMINDERS", "reminders", "off", "off"),
        ("COMPANION_OWN_MARKS", "own marks", "off", "off"),
        ("COMPANION_CRISIS", "crisis", "on", "live"),
        ("COMPANION_CALENDAR", "calendar", "off", "off"),
    ],
)
def test_a_switch_is_listed_where_it_stands(
    monkeypatch: pytest.MonkeyPatch, env: str, label: str, raw: str, row: str
) -> None:
    monkeypatch.setenv(env, raw)
    assert label in _row(row)
    assert all(label not in _row(other) for other in {"live", "shadow", "off"} - {row})


@pytest.mark.parametrize(
    ("env", "raw", "shown"),
    [
        ("COMPANION_REACH", "rare", "reach rare"),
        ("COMPANION_REACH", "", "reach warm"),
        ("COMPANION_ROUTE_INTIMATE", "on", "intimate may route"),
        ("COMPANION_HEDGED_PLANS", "off", "hedged plans strict"),
    ],
)
def test_a_dial_is_shown_with_its_value(
    monkeypatch: pytest.MonkeyPatch, env: str, raw: str, shown: str
) -> None:
    monkeypatch.setenv(env, raw)
    assert shown in _row("dials")


def test_the_platform_is_in_the_heading(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANION_PLATFORM", "discord")
    assert _lines()[0] == "up as t on discord"


def test_the_pace_is_shown_and_an_unknown_one_means_natural(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPANION_PACE", "slow")
    assert "pace slow" in _row("limits")
    monkeypatch.setenv("COMPANION_PACE", "warp")
    assert "pace natural" in _row("limits")


def test_an_override_and_no_roleplay_talker_are_shown_as_they_are(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPANION_EVERYDAY_MODEL", "some/model")
    assert _row("everyday") == ["some/model", "standby none"]
    assert _row("roleplay") == ["the everyday model"]


def test_judge_routes_are_shown_unless_there_are_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANION_JUDGE_ROUTES", "crisis=a/b,listen=c/d")
    assert " ".join(_row("judges")) == f"{JUDGE_MODEL} (crisis on a/b listen on c/d)"
    monkeypatch.setenv("COMPANION_JUDGE_ROUTES", "none")
    assert _row("judges") == [JUDGE_MODEL]


def test_the_startup_block_names_the_character() -> None:
    assert "character mika@local" in " ".join(_lines("mika"))


def test_every_switch_appears_once() -> None:
    shown = [x.split(" ")[0] for row in ("live", "shadow", "off", "dials") for x in _row(row)]
    labels = [s.label.split(" ")[0] for s in SWITCHES if s.label != "platform"]
    assert sorted(x for x in shown if x != "none") == sorted(labels)
