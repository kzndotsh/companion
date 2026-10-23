"""The notes a turn adds to the system block, and the look-ups they wait for."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, cast

from companion.core.ack import (
    inputs_hash,
)
from companion.core.basics import ASK_EVERY as ASK_NAME_EVERY
from companion.core.basics import ASKED as ASKED_NAME
from companion.core.basics import ask_name, knows_name
from companion.core.clock import local_zone, named_zone
from companion.core.episodes import GAP_BACK as EPISODE_GAP
from companion.core.episodes import NOTE as EPISODES_NOTE
from companion.core.episodes import Told, period
from companion.core.episodes import note as episodes_note
from companion.core.episodes import recent as recent_times
from companion.core.floor import BRUSH_NOTE, HOLD_NOTE
from companion.core.frames import (
    scene_note,
)
from companion.core.guess import INVITED as GUESS_INVITED
from companion.core.guess import NOTE as GUESS_NOTE
from companion.core.guess import likely as guess_likely
from companion.core.guess import note as guess_note
from companion.core.habits import habit_note
from companion.core.knowing import MAP_EVERY, WOULD_ASK, pick_gap
from companion.core.length import LengthTarget, length_target
from companion.core.listening import PROMPT as LISTEN_PROMPT
from companion.core.listening import listening_note, repair_note, rude_note
from companion.core.listening import render_reason as render_listening
from companion.core.mood import PARAMS_VERSION as MOOD_PARAMS
from companion.core.mood import WINDOW as MOOD_WINDOW
from companion.core.mood import Effect as MoodEffect
from companion.core.mood import Said, chat_minutes, effects_for, held_because, inputs_for, mood_at
from companion.core.mood import line as mood_line
from companion.core.mood import reason as mood_reason
from companion.core.openloops import LoopState, loop_note, loop_note_ref, pick_note
from companion.core.ownup import owned_note
from companion.core.recall import PROMPT as RECALL_PROMPT
from companion.core.recall import recall_note
from companion.core.relevance import GATE as RELEVANCE_GATE
from companion.core.relevance import LIVE as RELEVANCE_LIVE
from companion.core.relevance import SHOWN as RELEVANCE_SHOWN
from companion.core.topics import EVERY_TURNS as TOPIC_EVERY
from companion.core.topics import NOTE as TOPIC_NOTE
from companion.core.topics import SPENT as TOPIC_SPENT
from companion.core.topics import likely as topic_likely
from companion.core.topics import topic_note
from companion.core.types import (
    Belief,
    BeliefId,
    Frame,
    Json,
    Speaker,
    Utterance,
)
from companion.loops.episodes import write_closed
from companion.loops.features import Feature, Offer, Offered, quiet
from companion.loops.guess import Invited, invited_guess
from companion.loops.recall import Recalled, look_up
from companion.loops.registry import FEATURES
from companion.loops.relevance import shadow as relevance_look_up
from companion.loops.topics import judge_spent
from companion.prompts import get

if TYPE_CHECKING:
    from companion.loops.fast import Conversation
from companion.loops.turn import Heard, Turn, decide, is_casual, mark

log = logging.getLogger("companion.turn")
RELEVANT_NOTE = get("notes/relevant")
CHECK_IN_NOTE = get("notes/check-in")
CHECKED_IN = "check-in: asked how they are after a heavy last talk"
CHECK_IN_GAP = timedelta(hours=3)  # away at least this long since their last message
HEAVY_WINDOW = timedelta(hours=12)  # serious messages this close before it make it a heavy talk
SERIOUS = 2
LIVE_SECONDS = 3.0  # a slow look-up only means no memories are offered this turn
EPISODE_SECONDS = 8.0  # writing a just-ended stretch before the reply; slower means it is left out
LOOK_SECONDS = 9.0  # every look-up together; past it the reply goes without the late ones
EPISODES_SHOWN = "episodes: what the two of them did recently, shown"
LOOP_OFFERED = "open loop: offered as a note when they wrote"
LOOP_NOTE_EVERY = timedelta(hours=24)


@dataclass(frozen=True, slots=True)
class Lookups:
    """What a reply waits for besides the judges: a recall, whether a topic is spent, a guess."""

    recalled: Recalled | None = None
    spent: bool = False
    guess: Invited | None = None
    relevant: tuple[tuple[BeliefId, str], ...] = ()  # memories near their message (ADR 0018)
    recent: tuple[Told, ...] = ()  # what the two of them did recently, when it bears (J12, J49)
    found: Mapping[str, object] = field(default_factory=dict[str, object])  # by feature name


async def look(
    c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None, read: Heard | None
) -> Lookups:
    """Every look-up the reply waits for, run side by side under one deadline (LOOK_SECONDS). Each
    has its own limit too; one still running at the deadline, or one that raised, gives nothing
    this turn and the reply goes ahead. Before, they ran one after another and their limits stacked
    past 15 s (architecture audit, 2026-10-23)."""
    asked_to_recall = heard is not None and heard[0].recall

    async def no_guess() -> Invited | None:
        return None

    jobs: dict[str, Awaitable[object]] = {
        "recall": _recall(c, t, heard or read),
        "spent": _topic_spent(c, t, in_scene, heard),
        "guess": no_guess() if asked_to_recall else _invited_guess(c, t, in_scene, heard),
        "relevant": _relevant(c, t, in_scene, heard),
        "recent": _recent_times(c, t, in_scene),
        **{f.name: f.look(c, t, in_scene, heard) for f in FEATURES if f.look is not None},
    }
    tasks = {name: asyncio.ensure_future(job) for name, job in jobs.items()}
    _, late = await asyncio.wait(tasks.values(), timeout=LOOK_SECONDS)
    for task in late:
        task.cancel()
    got: dict[str, object] = {}
    for name, task in tasks.items():
        if task in late:
            log.warning("look-up %s still running at the turn's deadline; left out", name)
        elif task.exception() is not None:
            log.warning("look-up %s failed; left out: %r", name, task.exception())
        else:
            got[name] = task.result()
    return Lookups(
        recalled=cast("Recalled | None", got.get("recall")),
        spent=got.get("spent") is True,
        guess=cast("Invited | None", got.get("guess")),
        relevant=cast("tuple[tuple[BeliefId, str], ...]", got.get("relevant", ())),
        recent=cast("tuple[Told, ...]", got.get("recent", ())),
        found={f.name: got[f.name] for f in FEATURES if f.name in got},
    )


async def _recent_times(c: Conversation, t: Turn, in_scene: Frame) -> tuple[Told, ...]:
    """What the two of them did recently, when their words point at a time or they come back after
    a gap (J12, J49). A stretch not yet recorded is written first. Logged; shown only when on."""
    if c.episodes == "off" or c.judge is None or in_scene is not Frame.REAL:
        return ()
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    last = theirs[-1].at if theirs else None
    zone = named_zone()
    pointed = period(t.text, t.now, zone) is not None
    back = last is not None and t.now - last >= EPISODE_GAP
    if not (pointed or back):
        return ()
    mark(t, "recent times")
    try:
        await asyncio.wait_for(write_closed(c.store, c.judge, c.rel, t.now), EPISODE_SECONDS)
    except Exception as err:  # what is already recorded is still shown
        log.warning("writing episodes before the reply failed: %r", err)
    ends = [(e.start_at, e.end_at, e.gist) for e in c.store.episodes(c.rel)]
    told = recent_times(ends, t.text, last, t.now, zone)
    if told:
        detail: dict[str, Json] = {
            "mode": c.episodes,
            "why": "pointed at a time" if pointed else "back after a gap",
            "shown": [f"{x.when}: {x.gist}" for x in told],
            "note": EPISODES_NOTE.ref,
        }
        shadow = "" if c.episodes == "on" else " (shadow, not sent)"
        decide(c, t, EPISODES_SHOWN, detail, reason=EPISODES_SHOWN + shadow)
    return tuple(told) if c.episodes == "on" else ()


async def _relevant(
    c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None
) -> tuple[tuple[BeliefId, str], ...]:
    """With the look-up on (ADR 0018): the memories a small model picks as bearing on their message,
    asked only when the closest memory is near (GATE), outside a scene. Logged either way. With no
    listening read (the judge failed) it still runs, as a turn that is not sharing, so nothing held
    is offered."""
    if c.relevance != "on" or c.embedder is None or c.judge is None:
        return ()
    if in_scene is not Frame.REAL:
        return ()
    mark(t, "relevance look-up")
    replies = [u.text for u in t.prior if u.speaker is Speaker.COMPANION]
    found = await relevance_look_up(
        c.store,
        c.embedder,
        c.judge,
        c.rel,
        model=c.embed_model,
        said=t.text,
        last_reply=replies[-1] if replies else None,
        sharing=heard is not None and heard[0].severity >= 1,
        on_card=(),
        now=t.now,
        gate=RELEVANCE_GATE,
        timeout=LIVE_SECONDS,
    )
    if found is None:
        return ()
    decide(c, t, RELEVANCE_LIVE, found.detail)
    rows = found.detail.get("picked")
    return tuple(
        (BeliefId(str(row["id"])), str(row["claim"]))
        for row in (rows if isinstance(rows, list) else [])
        if isinstance(row, dict) and isinstance(row.get("claim"), str) and "id" in row
    )


async def _invited_guess(
    c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None
) -> Invited | None:
    """When their short question invites a guess about them (J16), what memory holds that may fit.
    Casual turns only; logged with what was offered, so guesses can later be scored by kind."""
    if c.judge is None or not is_casual(t, in_scene, heard) or not guess_likely(t.text):
        return None
    mark(t, "guess judge")
    found = await invited_guess(c.judge, t.prior, t.text, c.store.user_beliefs(c.rel))
    if found is not None:
        decide(
            c,
            t,
            GUESS_INVITED,
            {
                "about": found.about,
                "offered": [b.claim for b in found.offered],
                "note": GUESS_NOTE.ref,
            },
        )
    return found


async def _topic_spent(c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None) -> bool:
    """Whether a small topic has run its course: asked of its own judge only on a likely moment on
    a casual turn, so the listening judge, which carries the age floor, stays as it was."""
    if c.judge is None or not is_casual(t, in_scene, heard) or not topic_likely(t.prior, t.text):
        return False
    mark(t, "topic judge")
    return await judge_spent(c.judge, t.prior, t.text)


def _topic_note(m: Moment, *, quiet: bool, loop_offered: bool) -> Offer:
    """When a small topic has run its course, one line to move on, at most once in EVERY_TURNS of
    their messages. Recorded with the move it named once the reply is stored."""
    c, t = m.c, m.t
    if not m.looked.spent or "?" in t.text:
        return Offer()  # a question of theirs is answered, never moved past
    theirs = [u.turn_id for u in t.prior if u.speaker is Speaker.USER][-(TOPIC_EVERY - 1) :]
    recent = any(
        d.has_key(TOPIC_SPENT) for turn in theirs for d in c.store.decisions_for_turn(c.rel, turn)
    )
    found = topic_note(
        spent=True,
        casual=quiet,
        moved_recently=recent,
        local_hour=t.now.astimezone(local_zone()).hour,
        loop_offered=loop_offered,
    )
    if found is None:
        return Offer()
    note, move = found
    return Offer(
        (note,), (lambda: decide(c, t, TOPIC_SPENT, {"move": move.ref, "note": TOPIC_NOTE.ref}),)
    )


def _map_shadow(m: Moment, *, asking_name: bool) -> Offer:
    """The gap it would ask about on a casual turn, at most once a day (J48, shadow). Nothing
    reaches the talker. The name comes first, so nothing is picked while that note is offered."""
    c, t = m.c, m.t
    if not m.casual or asking_name or c.store.decided_since(c.rel, WOULD_ASK, t.now - MAP_EVERY):
        return Offer()
    gap = pick_gap(c.store.user_beliefs(c.rel), c.store.belief_labels(c.rel))
    if gap is None:
        return Offer()
    detail: dict[str, Json] = {
        "why": gap.reason,
        "domain": gap.domain.value,
        "depth": gap.depth.value,
        "counts": {d.value: n for d, n in gap.counts.items()},
    }
    return Offer(after=(lambda: decide(c, t, WOULD_ASK, detail),))


def _ask_name(m: Moment) -> Offer:
    """Offer to ask what to call them on a casual turn, at most once a day, until memory knows."""
    c, t = m.c, m.t
    note = ask_name(
        known=knows_name(m.beliefs),
        casual=m.casual,
        asked_recently=c.store.decided_since(c.rel, ASKED_NAME, t.now - ASK_NAME_EVERY),
    )
    return Offer() if note is None else Offer((note,), (lambda: decide(c, t, ASKED_NAME),))


def _loop_note(m: Moment, *, quiet: bool) -> Offer:
    """Bring up one due open loop as a note when they write (J15): on a casual turn with no other
    nudge, at most one a day, each loop at most twice. Once the reply is stored the loop is marked
    asked, so it is never also a reach-out."""
    c, t = m.c, m.t
    if not quiet or c.store.decided_since(c.rel, LOOP_OFFERED, t.now - LOOP_NOTE_EVERY):
        return Offer()
    offers = c.store.loop_events_with_reason(c.rel, LOOP_OFFERED)
    loop = pick_note(c.store.open_loops(c.rel), offers, t.now, local_zone())
    if loop is None:
        return Offer()
    detail: dict[str, Json] = {
        "loop_id": loop.id,
        "claim": loop.claim,
        "kind": loop.kind.value,
        "offer": offers.get(loop.id, 0) + 1,
        "note": loop_note_ref(loop),
    }

    def asked() -> None:
        c.store.open_loop_event(loop.id, LoopState.ASKED, LOOP_OFFERED, t.now)
        decide(c, t, LOOP_OFFERED, detail)

    note = loop_note(loop)
    return Offer((note,) if note else (), (asked,))


def _listening_note(c: Conversation, t: Turn, heard: Heard | None) -> str | None:
    """The line for the system block, with the decision logged from the labels."""
    if heard is None:
        return None
    judged, model, prompt = heard
    replies = [u.text for u in t.prior if u.speaker is Speaker.COMPANION]
    note = listening_note(judged, replies, seed=t.turn)
    decide(
        c,
        t,
        "listening",
        {
            "scorer": model,
            "prompt": LISTEN_PROMPT.ref,
            "inputs_hash": inputs_hash(prompt),
            "labels": {
                "intimate": judged.intimate,
                "severity": judged.severity,
                "stance": judged.stance,
                "vague": judged.vague,
                "rude": judged.rude,
            },
        },
        reason=render_listening(judged, note),
    )
    return note


async def _recall(c: Conversation, t: Turn, heard: Heard | None) -> Recalled | None:
    """When they asked it to remember something, look it up across all of memory and log it."""
    if c.judge is None or heard is None or not heard[0].recall or not heard[0].topic:
        return None
    mark(t, f"recall look-up: {heard[0].topic!r}")
    recalled = await look_up(c.judge, c.store.user_beliefs(c.rel), heard[0].topic)
    found = recalled.picked if recalled is not None else ()
    reason = f"recall: they asked about {heard[0].topic!r}; " + (
        f"{len(found)} found" if recalled is not None else "the look-up failed"
    )
    decide(
        c,
        t,
        "recall",
        {
            "topic": heard[0].topic,
            "picked": [b.id for b in found],
            "searched": recalled.searched if recalled is not None else 0,
            "scorer": recalled.model if recalled is not None else "",
            "prompt": RECALL_PROMPT.ref,
        },
        reason=reason,
    )
    return recalled


def _mood(
    c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None
) -> tuple[str | None, list[MoodEffect]]:
    """The mood line for the system block when the mood is on, and what this message adds to it.
    The decision is logged in shadow mode too, so the replay and the live log can be compared."""
    if c.mood == "off":
        return None, []
    zone = local_zone()
    severity = heard[0].severity if heard is not None else None
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    earlier = c.store.said_since(c.rel, theirs[-1].at)[:1] if theirs else []
    minutes = chat_minutes([u.at for u in t.prior], t.now, zone)
    said = Said(t.turn, t.now, t.text, severity, None)
    added = effects_for(inputs_for(said, earlier[0].tone if earlier else None, minutes))
    stored = c.store.mood_effects_since(c.rel, t.now - MOOD_WINDOW)
    before, after = mood_at(stored, t.now, zone), mood_at([*stored, *added], t.now, zone)
    held = held_because(severity=severity, text=t.text, in_scene=in_scene is not Frame.REAL)
    shown, why = mood_line(after, held=held), mood_reason(after, held=held)
    decide(
        c,
        t,
        "mood",
        {
            "mode": c.mood,
            "params": MOOD_PARAMS,
            "before": {s.value: round(v, 3) for s, v in before.strengths.items()},
            "after": {s.value: round(v, 3) for s, v in after.strengths.items()},
            "added": [[e.source.value, round(e.amount, 3)] for e in added],
            "line": shown,
        },
        reason=f"{why} [{c.mood}]",
    )
    return (shown if c.mood == "on" else None), added


def _notes(
    c: Conversation, prior: list[Utterance], in_scene: Frame, size: LengthTarget | None
) -> list[str]:
    """What it should know about its own habits, a scene in progress and how long to answer.
    These go in the system block with the memory card: in a user message the model read them as
    something they said."""
    notes = [habit_note(prior), c.habits.note(), scene_note(in_scene), size.note if size else None]
    return [n for n in notes if n is not None]


def _length(c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None) -> LengthTarget | None:
    """The one length target for this turn, logged with the reason code wrote for it."""
    severity = heard[0].severity if heard is not None else None
    size = length_target(
        t.text, severity=severity, in_scene=in_scene is not Frame.REAL, seed=str(t.turn)
    )
    reason = f"length: under about {size.words} words, {size.why}" if size else "length: no cap"
    decide(
        c, t, "length", {"words": size.words if size else None, "severity": severity}, reason=reason
    )
    return size


@dataclass(frozen=True, slots=True)
class Moment:
    """What every note reads about the turn being answered."""

    c: Conversation
    t: Turn
    in_scene: Frame
    heard: Heard | None
    looked: Lookups
    held: bool  # the floor held this turn (ADR 0017)
    beliefs: Sequence[Belief]  # the memories that may be stated as true
    on_card: frozenset[BeliefId] = frozenset()  # what the card already shows this turn
    brushed: bool = False  # they pushed the flirting or the scene back (`system/brush-off`)

    @property
    def casual(self) -> bool:
        return is_casual(self.t, self.in_scene, self.heard)


@dataclass(frozen=True, slots=True)
class Notes:
    lines: tuple[str, ...]
    after: tuple[Callable[[], None], ...]
    tail: tuple[str, ...] = ()


def _base(m: Moment, _: Offered) -> Offer:
    size = _length(m.c, m.t, m.in_scene, m.heard)
    return Offer(tuple(_notes(m.c, m.t.prior, m.in_scene, size)))


def _listening(m: Moment, _: Offered) -> Offer:
    note = _listening_note(m.c, m.t, m.heard)
    return Offer((note,) if note else ())


def _rude(m: Moment, _: Offered) -> Offer:
    note = rude_note(m.heard[0]) if m.heard is not None else None
    return Offer((note,) if note else ())


def _repair(m: Moment, _: Offered) -> Offer:
    note = repair_note(m.heard[0]) if m.heard is not None else None
    return Offer((note,) if note else ())


def _owned(m: Moment, so_far: Offered) -> Offer:
    """When one of its last replies owned a slip, a note not to own more: outside a scene, and not
    when they say it got them wrong this turn (the repair note's). Sent after the history: in the
    system block it moved nothing (measured 2026-10-22)."""
    if m.in_scene is not Frame.REAL:
        return Offer()
    replies = [u.text for u in m.t.prior if u.speaker is Speaker.COMPANION]
    note = owned_note(replies, repairing=bool(so_far["repair"].lines))
    return Offer(tail=(note,) if note else ())


def _recalled(m: Moment, _: Offered) -> Offer:
    recalled = m.looked.recalled
    if recalled is None:
        return Offer()
    # In a scene an empty look-up adds nothing: what they mean is most likely in the story itself,
    # in view, and "memory holds nothing" would make it deny something it can see.
    if m.in_scene is not Frame.REAL and not recalled.picked:
        return Offer()
    note = recall_note(recalled.picked)
    return Offer((note,) if note else ())


def _mood_line(m: Moment, _: Offered) -> Offer:
    shown, added = _mood(m.c, m.t, m.in_scene, m.heard)
    c = m.c
    after = (lambda: c.store.add_mood_effects(c.rel, added),) if added else ()
    return Offer((shown,) if shown else (), after)


def _severity(detail: dict[str, Json] | None) -> int:
    """The severity a listening decision logged, or -1."""
    labels = (detail or {}).get("labels")
    value = labels.get("severity") if isinstance(labels, dict) else None
    return value if isinstance(value, int) else -1


def _check_in(m: Moment, _: Offered) -> Offer:
    """When they come back after a gap and the talk before it was heavy (a serious message in its
    last hours), one note to ask gently how they are, once per heavy talk."""
    c, t = m.c, m.t
    if m.heard is None or m.heard[0].severity >= SERIOUS or m.in_scene is not Frame.REAL:
        return Offer()
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    if not theirs or t.now - theirs[-1].at < CHECK_IN_GAP:
        return Offer()
    last = theirs[-1].at
    if c.store.decided_since(c.rel, CHECKED_IN, last):
        return Offer()
    recent = [u.turn_id for u in theirs if last - u.at <= HEAVY_WINDOW]
    heavy = any(
        _severity(d.detail) >= SERIOUS
        for turn in recent
        for d in c.store.decisions_for_turn(c.rel, turn)
        if d.has_key("listening")
    )
    if not heavy:
        return Offer()
    return Offer((CHECK_IN_NOTE.text,), (lambda: decide(c, t, CHECKED_IN),))


def _hold(m: Moment, _: Offered) -> Offer:
    return Offer((HOLD_NOTE.text,) if m.held else ())


def _brush(m: Moment, _: Offered) -> Offer:
    return Offer((BRUSH_NOTE.text,) if m.brushed else ())


def _name(m: Moment, so_far: Offered) -> Offer:
    return Offer() if so_far["check-in"].lines else _ask_name(m)


def _quiet(m: Moment, so_far: Offered) -> bool:
    return quiet(m, so_far)


def _map(m: Moment, so_far: Offered) -> Offer:
    return _map_shadow(m, asking_name=bool(so_far["name"].lines))


def _loop(m: Moment, so_far: Offered) -> Offer:
    return _loop_note(m, quiet=_quiet(m, so_far))


def _topic(m: Moment, so_far: Offered) -> Offer:
    return _topic_note(m, quiet=_quiet(m, so_far), loop_offered=bool(so_far["loop"].lines))


def _relevant_note(m: Moment, _: Offered) -> Offer:
    picks = [claim for bid, claim in m.looked.relevant if bid not in m.on_card][:RELEVANCE_SHOWN]
    if not picks:
        return Offer()
    return Offer((RELEVANT_NOTE.render(items="\n".join(f"- {p}" for p in picks)),))


def _recent_note(m: Moment, _: Offered) -> Offer:
    text = episodes_note(m.looked.recent)
    return Offer((text,) if text else ())


def _guess(m: Moment, _: Offered) -> Offer:
    g = m.looked.guess
    note = guess_note(g.about, g.offered) if g is not None else None
    return Offer((note,) if note else ())


def _feature_note(f: Feature) -> Callable[[Moment, Offered], Offer]:
    note = f.note
    assert note is not None

    def source(m: Moment, so_far: Offered) -> Offer:
        return note(m, m.looked.found.get(f.name), so_far)

    return source


# Every note, in the order it reaches the system block. A source sees what the ones before it
# offered: a plan or a move on waits while their name is asked, a move on knows a plan was offered.
SOURCES: tuple[tuple[str, Callable[[Moment, Offered], Offer]], ...] = (
    ("base", _base),
    ("listening", _listening),
    ("rude", _rude),
    ("repair", _repair),
    ("owned", _owned),
    ("recall", _recalled),
    ("relevant", _relevant_note),
    ("recent", _recent_note),
    ("check-in", _check_in),
    ("mood", _mood_line),
    ("hold", _hold),
    ("brush-off", _brush),
    ("name", _name),
    ("map", _map),
    ("loop", _loop),
    ("topic", _topic),
    ("guess", _guess),
    *((f.name, _feature_note(f)) for f in FEATURES if f.note is not None),
)


def notes_for(m: Moment) -> Notes:
    """Every note for this turn, in order, and the writes to make once the reply is stored."""
    offered: dict[str, Offer] = {}
    for name, source in SOURCES:
        offered[name] = source(m, offered)
    return Notes(
        tuple(line for o in offered.values() for line in o.lines),
        tuple(f for o in offered.values() for f in o.after),
        tuple(line for o in offered.values() for line in o.tail),
    )
