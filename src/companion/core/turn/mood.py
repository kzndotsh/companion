"""A mood that carries (ADR 0016): a few named states, owned by code, shown only in behaviour.

What happens in a turn becomes effects: each adds strength to one state, fades with that state's
half-life, and is kept in an append-only table. The mood at any moment is worked out from the
effects, never stored, so it fades without anything running, survives a restart and replays
exactly.

Only what the user did can move it. There is no source for silence, a goodbye, a gap, a failed
call or an undelivered reply, so none of them can lower or raise a state.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from enum import StrEnum
from itertools import pairwise

from companion.core.turn.energy import texting_energy
from companion.core.types import TurnId
from companion.prompts import get

PARAMS_VERSION = "1"
LINE_AT = 0.3  # a state shows only at or above this strength
MAX_SHOWN = 2
SERIOUS = (
    2  # the listening severity at which a turn starts tender and every other state holds still
)


class State(StrEnum):
    COZY = "cozy"
    TENDER = "tender"
    PLAYFUL = "playful"


class Source(StrEnum):
    CHAT_SPAN = "chat_span"  # minutes chatted today
    LONG_CHAT = "long_chat"  # a long chat leaves a little warmth into the next day
    TONE_SWEET = "tone_sweet"  # the react judge read their last message as sweet
    TONE_FUNNY = "tone_funny"  # ... or as funny
    ENERGY = "energy"  # typed with energy, on a message that is not serious
    SERIOUS = "serious"  # the listening judge rated it serious
    EASED = "eased"  # play after something hard: a sign they are fine, so tender fades sooner


@dataclass(frozen=True, slots=True)
class Rule:
    state: State
    half_life_hours: float
    cap: float


RULES: Mapping[Source, Rule] = {
    Source.CHAT_SPAN: Rule(State.COZY, 4, 0.5),
    Source.LONG_CHAT: Rule(State.COZY, 24, 0.15),
    Source.TONE_SWEET: Rule(State.COZY, 3, 0.3),
    Source.TONE_FUNNY: Rule(State.PLAYFUL, 2, 0.4),
    Source.ENERGY: Rule(State.PLAYFUL, 2, 0.3),
    Source.SERIOUS: Rule(State.TENDER, 12, 0.8),
    Source.EASED: Rule(State.TENDER, 12, 0.2),
}

# A source that takes away from its state instead of adding. It fades at the same pace as what it
# eases, so the state cannot come back once it has eased, and it counts only after the latest effect
# that raised that state, so play before something hard does not soften the next one. Unlike every
# other source, easing adds up: each further sign that they are fine takes off a little more.
EASING = frozenset({Source.EASED})

# The first state holds the second back: weakened by it, and gone while the first shows, so there
# is never teasing while tender.
HOLDS_BACK: tuple[tuple[State, State], ...] = ((State.TENDER, State.PLAYFUL),)

NIGHT_HOURS = frozenset({22, 23, 0, 1, 2})
NIGHT_COZY = 0.35  # late at night it leans cozy: calmer, unhurried, a bit shorter

CHAT_SPAN_FROM_MINUTES = 15
LONG_CHAT_MINUTES = 60
ENERGY_FROM = 2
CHAT_GAP = timedelta(minutes=10)  # a longer pause ends a stretch of chatting
WINDOW = timedelta(days=5)  # how far back a caller reads effects; the longest half-life is a day


@dataclass(frozen=True, slots=True)
class Effect:
    state: State
    source: Source
    amount: float
    half_life_hours: float
    at: datetime
    turn: TurnId

    def left(self, now: datetime) -> float:
        """What is left of this effect at `now`. Nothing before it happened."""
        if now < self.at:
            return 0.0
        hours = (now - self.at) / timedelta(hours=1)
        return self.amount * 0.5 ** (hours / self.half_life_hours)


@dataclass(frozen=True, slots=True)
class Inputs:
    """What a turn knows that can move the mood. `severity` is None when the listening judge failed
    or is off, and `tone` is None when there was no reaction judgement on their previous message."""

    at: datetime
    turn: TurnId
    chat_minutes: float
    energy: int
    tone: str | None
    severity: int | None


@dataclass(frozen=True, slots=True)
class Mood:
    strengths: Mapping[State, float]
    sources: Mapping[
        State, tuple[Source, ...]
    ]  # what is still holding each state up, strongest first

    def shown(self) -> list[State]:
        """The strongest states at or above the line, at most two."""
        ranked = sorted(self.strengths, key=lambda s: (-self.strengths[s], s.value))
        return [s for s in ranked if self.strengths[s] >= LINE_AT][:MAX_SHOWN]


def effect(source: Source, amount: float, at: datetime, turn: TurnId) -> Effect:
    """An effect from one source, held to that source's cap."""
    if at.tzinfo is None:
        msg = "a mood effect needs an aware time"
        raise ValueError(msg)
    rule = RULES[source]
    return Effect(
        rule.state, source, min(max(amount, 0.0), rule.cap), rule.half_life_hours, at, turn
    )


def effects_for(i: Inputs) -> list[Effect]:
    """What one turn adds. A serious turn adds tender and nothing else, so every other state
    holds. Without a listening judgement nothing is added: an unread message could have been
    serious, and a failed call never moves the mood."""
    if i.severity is None:
        return []
    if i.severity >= SERIOUS:
        return [effect(Source.SERIOUS, RULES[Source.SERIOUS].cap, i.at, i.turn)]
    out: list[Effect] = []
    if i.chat_minutes >= CHAT_SPAN_FROM_MINUTES:
        out.append(effect(Source.CHAT_SPAN, i.chat_minutes / 120, i.at, i.turn))
    if i.chat_minutes >= LONG_CHAT_MINUTES:
        out.append(effect(Source.LONG_CHAT, RULES[Source.LONG_CHAT].cap, i.at, i.turn))
    if i.tone == "sweet":
        out.append(effect(Source.TONE_SWEET, RULES[Source.TONE_SWEET].cap, i.at, i.turn))
    if i.tone == "funny":
        out.append(effect(Source.TONE_FUNNY, RULES[Source.TONE_FUNNY].cap, i.at, i.turn))
    if i.severity == 0 and i.energy >= ENERGY_FROM:
        out.append(effect(Source.ENERGY, 0.1 * i.energy, i.at, i.turn))
    if any(e.state is State.PLAYFUL for e in out):
        out.append(effect(Source.EASED, RULES[Source.EASED].cap, i.at, i.turn))
    return out


def mood_at(effects: Iterable[Effect], now: datetime, zone: tzinfo) -> Mood:
    """The mood at `now`. A repeat from the same source restarts the timer at the larger of what
    was left and what it brings, never adding to it; with one half-life per source that comes to
    the strongest single effect still left, so the order effects are read in cannot matter. Easing
    adds up, and only what came after the latest effect that raised the state takes it away. A
    state holds back its opposite, and nothing falls below the time of day's baseline."""
    past = [e for e in effects if e.at <= now]
    raised: dict[State, datetime] = {}
    for e in past:
        if e.source not in EASING and (e.state not in raised or e.at > raised[e.state]):
            raised[e.state] = e.at
    left: dict[Source, tuple[float, State]] = {}
    for e in past:
        if e.source in EASING and (e.state not in raised or e.at < raised[e.state]):
            continue
        value = e.left(now)
        if e.source in EASING:
            left[e.source] = (left.get(e.source, (0.0, e.state))[0] + value, e.state)
        elif e.source not in left or value > left[e.source][0]:
            left[e.source] = (value, e.state)
    after = dict.fromkeys(State, 0.0)
    for source in sorted(left, key=lambda x: x.value):
        value, state = left[source]
        after[state] += -value if source in EASING else value
    after = {s: max(0.0, v) for s, v in after.items()}
    for holder, held in HOLDS_BACK:
        after[held] = 0.0 if after[holder] >= LINE_AT else max(0.0, after[held] - after[holder])
    floor = baseline(now, zone)
    strengths = {s: min(1.0, max(after[s], floor.get(s, 0.0))) for s in State}
    ranked = sorted(left, key=lambda x: (-left[x][0], x.value))
    sources = {
        s: tuple(x for x in ranked if left[x][1] is s and x not in EASING and after[s] > 0)
        for s in State
    }
    return Mood(strengths, sources)


def baseline(now: datetime, zone: tzinfo) -> dict[State, float]:
    """The floor the time of day sets: cozy late at night, nothing otherwise."""
    return {State.COZY: NIGHT_COZY} if now.astimezone(zone).hour in NIGHT_HOURS else {}


_LEAVING = re.compile(
    r"\b(?:bye+|goodbye|cya|see ya|ttyl|talk (?:to you )?later|gtg|g2g|gotta (?:go|run|head)"
    r"|got to go|have to go|heading (?:to bed|out|off)|(?:going|off) to (?:bed|sleep)|sleep well)\b"
    r"|(?:^|[,.!]\s*|\b(?:ok|okay|alright|well)\s+)(?:good ?night|night night|nite|night|gn)\b",
    re.IGNORECASE,
)


def held_because(*, severity: int | None, text: str, in_scene: bool) -> str | None:
    """Why no mood line is shown this turn, or None. A serious turn has the listening note, a
    goodbye must never get a mood that could read as a pull to stay, and a scene has its voice."""
    if severity is not None and severity >= SERIOUS:
        return "the turn is serious"
    if in_scene:
        return "a scene is in progress"
    if _LEAVING.search(text):
        return "they are leaving"
    return None


def line(mood: Mood, *, held: str | None) -> str | None:
    """The note for the system block, or None when no state is strong enough or it is held."""
    if held is not None:
        return None
    shown = mood.shown()
    return "\n".join(get(f"notes/mood-{s.value}").text for s in shown) or None


def reason(mood: Mood, *, held: str | None) -> str:
    """The logged reason, written by code: `mood: cozy 0.42 (chat_span, tone_sweet)`."""
    if held is not None:
        return f"mood: held, {held}"
    parts = [f"{s.value} {mood.strengths[s]:.2f} ({_held_by(mood, s)})" for s in mood.shown()]
    return "mood: " + ("; ".join(parts) or "none strong enough")


def _held_by(mood: Mood, state: State) -> str:
    return ", ".join(x.value for x in mood.sources[state]) or "baseline"


@dataclass(frozen=True, slots=True)
class Said:
    """One message from them, with what the judges logged about it: the listening severity (None
    when it was not read) and the react judge's tone (None when not judged)."""

    turn: TurnId
    at: datetime
    text: str
    severity: int | None
    tone: str | None


def chat_minutes(times: Sequence[datetime], now: datetime, zone: tzinfo) -> float:
    """Minutes spent chatting today up to `now`: the gaps between messages that are no longer than
    a pause, counted from local midnight."""
    today = now.astimezone(zone).date()
    stamps = sorted(t for t in times if t <= now and t.astimezone(zone).date() == today)
    stamps.append(now)
    gaps = (b - a for a, b in pairwise(stamps))
    return sum((g for g in gaps if g <= CHAT_GAP), timedelta()) / timedelta(minutes=1)


def inputs_for(said: Said, previous_tone: str | None, minutes: float) -> Inputs:
    """What a message brings to the mood. The tone is the one judged on their previous message,
    because a message's own tone is judged beside the reply, after the mood is read."""
    return Inputs(
        said.at, said.turn, minutes, texting_energy(said.text), previous_tone, said.severity
    )


@dataclass(frozen=True, slots=True)
class Replayed:
    said: Said
    mood: Mood
    line: str | None
    added: tuple[Effect, ...]


def replay(said: Sequence[Said], times: Sequence[datetime], zone: tzinfo) -> list[Replayed]:
    """What the mood would have been on each of their messages, from the same rules the bot uses."""
    effects: list[Effect] = []
    out: list[Replayed] = []
    previous: str | None = None
    for s in sorted(said, key=lambda s: s.at):
        added = effects_for(inputs_for(s, previous, chat_minutes(times, s.at, zone)))
        effects += added
        mood = mood_at(effects, s.at, zone)
        held = held_because(severity=s.severity, text=s.text, in_scene=False)
        out.append(Replayed(s, mood, line(mood, held=held), tuple(added)))
        previous = s.tone
    return out
