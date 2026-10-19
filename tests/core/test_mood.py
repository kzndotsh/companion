from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo

import pytest

from companion import prompts
from companion.core.mood import (
    LINE_AT,
    Inputs,
    Source,
    State,
    effect,
    effects_for,
    line,
    mood_at,
    reason,
)
from companion.core.types import TurnId

DAY = datetime(2026, 10, 19, 14, 0, tzinfo=UTC)
NIGHT = datetime(2026, 10, 19, 23, 30, tzinfo=UTC)
T = TurnId("t")


def _in(at: datetime = DAY, **kw: object) -> Inputs:
    base: dict[str, object] = {
        "at": at,
        "turn": T,
        "chat_minutes": 0.0,
        "energy": 0,
        "tone": None,
        "severity": 0,
    }
    return Inputs(**{**base, **kw})  # pyright: ignore[reportArgumentType]


def test_a_repeat_from_one_source_refreshes_the_timer_instead_of_stacking() -> None:
    once = [effect(Source.TONE_FUNNY, 1, DAY, T)]
    twice = [*once, effect(Source.TONE_FUNNY, 1, DAY + timedelta(minutes=10), T)]
    later = DAY + timedelta(minutes=10)
    assert mood_at(twice, later, UTC).strengths[State.PLAYFUL] == pytest.approx(0.4)
    assert mood_at(once, later, UTC).strengths[State.PLAYFUL] < 0.4


def test_each_source_is_held_to_its_cap() -> None:
    [e] = [e for e in effects_for(_in(energy=50)) if e.source is Source.ENERGY]
    assert e.amount == pytest.approx(0.3)


def test_tender_and_playful_cancel_so_they_never_both_show() -> None:
    hard = effects_for(_in(severity=2))
    fun = effects_for(_in(DAY + timedelta(hours=1), tone="funny"))
    mood = mood_at([*hard, *fun], DAY + timedelta(hours=1), UTC)
    assert not {State.TENDER, State.PLAYFUL} <= set(mood.shown())


def test_a_lively_joke_right_after_something_hard_still_gets_no_teasing() -> None:
    hard = effects_for(_in(severity=2))
    fun = effects_for(_in(DAY + timedelta(minutes=30), tone="funny", energy=5))
    mood = mood_at([*hard, *fun], DAY + timedelta(minutes=30), UTC)
    assert mood.shown() == [State.TENDER]


def test_play_after_something_hard_eases_tender_sooner() -> None:
    hard = effects_for(_in(severity=2))
    fun = effects_for(_in(DAY + timedelta(hours=2), tone="funny"))
    at = DAY + timedelta(hours=3)
    alone = mood_at(hard, at, UTC).strengths[State.TENDER]
    eased = mood_at([*hard, *fun], at, UTC).strengths[State.TENDER]
    assert eased < alone


def test_tender_lasts_about_a_day() -> None:
    hard = effects_for(_in(severity=2))
    assert State.TENDER in mood_at(hard, DAY + timedelta(hours=1), UTC).shown()
    assert State.TENDER in mood_at(hard, DAY + timedelta(hours=10), UTC).shown()
    assert State.TENDER not in mood_at(hard, DAY + timedelta(hours=24), UTC).shown()


@pytest.mark.parametrize("severity", [2, 3])
def test_a_serious_turn_adds_only_tender_so_every_other_state_holds(severity: int) -> None:
    out = effects_for(_in(severity=severity, chat_minutes=90, tone="sweet", energy=6))
    assert [e.source for e in out] == [Source.SERIOUS]


@pytest.mark.parametrize("severity", [0, 1, None])
def test_only_a_serious_turn_starts_tender(severity: int | None) -> None:
    out = effects_for(_in(severity=severity, chat_minutes=90, tone="sweet", energy=6))
    assert Source.SERIOUS not in {e.source for e in out}
    assert mood_at(out, DAY, UTC).strengths[State.TENDER] == 0


@pytest.mark.parametrize(("severity", "counts"), [(0, True), (1, False), (None, False)])
def test_energy_counts_only_on_a_message_judged_not_serious(
    severity: int | None, *, counts: bool
) -> None:
    out = effects_for(_in(severity=severity, energy=5))
    assert (Source.ENERGY in {e.source for e in out}) is counts


def test_silence_only_fades_toward_the_baseline_and_never_below() -> None:
    warm = effects_for(_in(NIGHT - timedelta(hours=1), chat_minutes=90, tone="sweet"))
    hours = [NIGHT + timedelta(hours=h) for h in range(72)]
    cozy = [mood_at(warm, at, UTC).strengths[State.COZY] for at in hours]
    assert all(
        b <= a + 1e-9 or at.hour in {22, 23}
        for a, b, at in zip(cozy, cozy[1:], hours[1:], strict=False)
    )
    assert all(c >= 0.35 for c, at in zip(cozy, hours, strict=True) if at.hour in {22, 23, 0, 1, 2})
    assert all(c >= 0 for c in cozy)


def test_late_at_night_it_leans_cozy_and_by_day_there_is_no_line() -> None:
    assert mood_at([], NIGHT, UTC).shown() == [State.COZY]
    assert mood_at([], DAY, UTC).shown() == []
    assert line(mood_at([], DAY, UTC), serious_now=False) is None


def test_a_long_warm_chat_leaves_a_little_cozy_into_the_next_day() -> None:
    long = effects_for(_in(chat_minutes=90))
    next_day = DAY + timedelta(hours=20)
    assert mood_at(long, next_day, UTC).strengths[State.COZY] > 0
    assert mood_at(effects_for(_in(chat_minutes=20)), next_day, UTC).strengths[State.COZY] < 0.01


def test_the_line_shows_the_strongest_states_as_their_notes_and_never_on_a_serious_turn() -> None:
    mood = mood_at(effects_for(_in(NIGHT, tone="funny")), NIGHT, UTC)
    assert mood.shown() == [State.PLAYFUL, State.COZY]
    assert line(mood, serious_now=False) == "\n".join(
        [prompts.get("notes/mood-playful").text, prompts.get("notes/mood-cozy").text]
    )
    assert line(mood, serious_now=True) is None
    assert reason(mood, serious_now=True) == "mood: held, the turn is serious"
    assert (
        reason(mood, serious_now=False) == "mood: playful 0.40 (tone_funny); cozy 0.35 (baseline)"
    )


def test_a_weak_state_shows_nothing() -> None:
    mood = mood_at([effect(Source.TONE_SWEET, 0.1, DAY, T)], DAY, UTC)
    assert mood.strengths[State.COZY] < LINE_AT
    assert reason(mood, serious_now=False) == "mood: none strong enough"


def test_the_mood_is_the_same_whatever_order_the_effects_are_read_in() -> None:
    effects = [
        e
        for h in range(12)
        for e in effects_for(
            _in(
                DAY + timedelta(minutes=17 * h),
                chat_minutes=10 * h,
                tone="funny" if h % 3 else "sweet",
            )
        )
    ]
    at = DAY + timedelta(hours=4)
    shuffled = effects[:]
    random.Random(3).shuffle(shuffled)
    assert mood_at(effects, at, UTC) == mood_at(shuffled, at, UTC)


def test_an_effect_after_the_moment_asked_about_is_ignored() -> None:
    earlier = effects_for(_in(DAY, tone="funny"))
    later = effects_for(_in(DAY + timedelta(hours=1), tone="funny"))
    assert mood_at(later, DAY, UTC).strengths[State.PLAYFUL] == 0
    between = DAY + timedelta(minutes=30)
    assert mood_at([*earlier, *later], between, UTC) == mood_at(earlier, between, UTC)


def test_once_play_has_eased_tender_it_does_not_come_back_as_the_play_fades() -> None:
    hard = effects_for(_in(severity=2))
    fun = effects_for(_in(DAY + timedelta(hours=2), tone="funny"))
    hours = [DAY + timedelta(hours=2, minutes=30 * k) for k in range(40)]
    tender = [mood_at([*hard, *fun], at, UTC).strengths[State.TENDER] for at in hours]
    assert all(b <= a + 1e-9 for a, b in pairwise(tender))


def test_play_before_something_hard_does_not_soften_it() -> None:
    fun = effects_for(_in(DAY - timedelta(hours=1), tone="funny"))
    hard = effects_for(_in(severity=2))
    assert mood_at([*fun, *hard], DAY, UTC) == mood_at(hard, DAY, UTC)


def test_without_a_listening_judgement_nothing_moves() -> None:
    assert effects_for(_in(severity=None, chat_minutes=90, tone="funny", energy=6)) == []


def test_a_milder_repeat_never_lowers_what_is_left() -> None:
    strong = effect(Source.ENERGY, 0.3, DAY, T)
    milder = effect(Source.ENERGY, 0.2, DAY + timedelta(minutes=1), T)
    at = DAY + timedelta(minutes=1)
    assert mood_at([strong, milder], at, UTC).strengths[State.PLAYFUL] >= strong.left(at)
    later = DAY + timedelta(hours=3)
    kept = mood_at([strong, milder], later, UTC).strengths[State.PLAYFUL]
    assert kept == pytest.approx(strong.left(later))


def test_after_play_tender_drops_below_the_line_hours_sooner() -> None:
    hard = effects_for(_in(severity=2))
    fun = effects_for(_in(DAY + timedelta(hours=1), tone="funny"))
    at = DAY + timedelta(hours=6)
    assert State.TENDER in mood_at(hard, at, UTC).shown()
    assert State.TENDER not in mood_at([*hard, *fun], at, UTC).shown()


def test_the_night_is_read_in_the_local_zone() -> None:
    zone = ZoneInfo("America/New_York")
    late_there = datetime(2026, 10, 20, 3, 30, tzinfo=UTC)
    evening_there = datetime(2026, 10, 19, 23, 30, tzinfo=UTC)
    assert mood_at([], late_there, zone).shown() == [State.COZY]
    assert mood_at([], evening_there, zone).shown() == []


def test_order_does_not_matter_with_something_hard_and_play_mixed_in() -> None:
    effects = [
        *effects_for(_in(severity=2)),
        *effects_for(_in(DAY + timedelta(hours=1), tone="funny", energy=4)),
        *effects_for(_in(DAY + timedelta(hours=1), tone="funny", energy=2)),
        *effects_for(_in(DAY + timedelta(hours=2), severity=3)),
        *effects_for(_in(DAY + timedelta(hours=3), tone="sweet", chat_minutes=70)),
    ]
    at = DAY + timedelta(hours=4)
    for seed in range(5):
        shuffled = effects[:]
        random.Random(seed).shuffle(shuffled)
        assert mood_at(shuffled, at, UTC) == mood_at(effects, at, UTC)


def test_an_effect_needs_an_aware_time() -> None:
    with pytest.raises(ValueError, match="aware"):
        effect(Source.TONE_FUNNY, 0.4, datetime(2026, 10, 19, 14, 0), T)  # noqa: DTZ001


def test_something_hard_still_to_come_does_not_change_the_mood_before_it() -> None:
    hard = effects_for(_in(severity=2))
    fun = effects_for(_in(DAY + timedelta(hours=1), tone="funny"))
    later_hard = effects_for(_in(DAY + timedelta(hours=5), severity=2))
    at = DAY + timedelta(hours=2)
    assert mood_at([*hard, *fun, *later_hard], at, UTC) == mood_at([*hard, *fun], at, UTC)
