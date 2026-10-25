from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from companion.core.rhythm import learn
from companion.features.reach.logic import (
    Dial,
    Kind,
    Look,
    Pool,
    Thing,
    checked,
    choose,
    consider,
    dial,
    needy,
    pick_thing,
    step_down,
)

NOW = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)  # 3 PM, a usual hour on the baseline
THING = Thing("memory", "b1", "they are learning to bake bread")


def _look(**over: object) -> Look:
    base = Look(
        now=NOW,
        tz=UTC,
        rhythm=learn([], NOW, UTC),
        last_theirs=NOW - timedelta(hours=13),  # past the 12h baseline pause
        earlier=None,
        kept=15,
        last_kept=None,
        last_thought=None,
        thing=THING,
    )
    return replace(base, **over)  # pyright: ignore[reportArgumentType]


def _kind(look: Look) -> Kind | None:
    pick = choose(consider(look))
    return None if pick is None else pick.kind


def test_every_kind_is_weighed_and_the_first_that_applies_goes() -> None:
    assert [c.kind for c in consider(_look())] == list(Kind)
    assert _kind(_look(earlier=Kind.PLAN)) is Kind.PLAN
    assert _kind(_look(earlier=Kind.AWAY)) is Kind.AWAY
    assert _kind(_look()) is Kind.KEPT
    assert _kind(_look(kept=None)) is Kind.THOUGHT
    assert _kind(_look(kept=None, thing=None)) is Kind.MISSING


def test_each_kind_holds_with_a_reason_of_its_own() -> None:
    assert _kind(_look(last_kept=NOW - timedelta(days=1), thing=None)) is Kind.MISSING
    assert _kind(_look(kept=8, last_thought=NOW - timedelta(hours=3))) is Kind.MISSING
    early = _look(kept=None, last_theirs=NOW - timedelta(hours=4))  # under half of 12h
    assert _kind(early) is None
    assert all(c.why for c in consider(early))


def test_missing_them_and_a_thought_wait_for_a_usual_hour() -> None:
    night = NOW.replace(hour=3)
    look = _look(now=night, kept=None, last_theirs=night - timedelta(hours=13))
    assert _kind(look) is None


def test_a_thought_is_never_a_sensitive_memory_and_never_one_used_lately() -> None:
    pool = Pool(
        memories=[("m2", "a health worry", 2), ("m3", "a private matter", 3), ("m0", "a show", 0)],
        tastes=[],
        episodes=[],
    )
    assert pick_thing(pool, frozenset(), "2026-10-20") == Thing("memory", "m0", "a show")
    assert pick_thing(pool, frozenset({"m0"}), "2026-10-20") is None


def test_the_pick_is_the_same_for_the_same_seed() -> None:
    pool = Pool(
        memories=[(f"m{i}", f"thread {i}", 1) for i in range(6)],
        tastes=[("t1", "it likes rainy mornings")],
        episodes=[("e1", "a long chat about a game")],
    )
    first = pick_thing(pool, frozenset(), "2026-10-20")
    assert first is not None
    assert all(pick_thing(pool, frozenset(), "2026-10-20") == first for _ in range(5))
    days = {pick_thing(pool, frozenset(), f"2026-10-{d}") for d in range(10, 30)}
    assert len(days) > 1


def test_the_dial_reads_its_values_and_steps_down_one_level() -> None:
    assert dial("normal") is Dial.NORMAL
    assert dial("pushy") is Dial.WARM
    assert step_down(Dial.WARM) is Dial.NORMAL
    assert step_down(Dial.RARE) is Dial.OFF
    assert step_down(Dial.OFF) is Dial.OFF


@pytest.mark.parametrize(
    "draft",
    [
        "been waiting to hear from you all day",
        "did you forget about me?",
        "you've been quiet, everything okay?",
        "where have you been??",
        "it's been ages since we talked",
        "haven't heard from you in a bit",
        "why did you go quiet on me",
        "are you okay? haven't seen you",
        "reply when you see this, it's urgent",
        "guess what happened!!",
        "don't ignore me lol",
        "it's lonely here without you",
        "3 days and nothing huh",
    ],
)
def test_a_needy_draft_is_dropped(draft: str) -> None:
    assert needy(draft) is not None
    assert checked(draft) == ("", needy(draft))


@pytest.mark.parametrize(
    "draft",
    [
        "thought of you when that song came on, still on repeat?",
        "morning! how's the bread coming along?",
        "missed you a little today 🙂 how did the climb go?",
        "can't wait to hear how the trip went",
        "random thought: rainy mornings are the best for tea. you a tea person?",
    ],
)
def test_a_light_draft_is_kept_as_written(draft: str) -> None:
    assert needy(draft) is None
    assert checked(draft) == (draft, None)


def test_a_long_draft_goes_whole_and_an_empty_one_is_dropped() -> None:
    long = "thought of you when i saw a dog in a tiny raincoat today, so done with everything"
    assert checked(long) == (long, None)
    assert checked("   ") == ("", "empty")
