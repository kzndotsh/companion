"""The notes a turn adds to the system block, and the look-ups they wait for."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, cast

from companion.core.frames import (
    scene_note,
)
from companion.core.recall import PROMPT as RECALL_PROMPT
from companion.core.recall import recall_note
from companion.core.turn.ack import (
    inputs_hash,
)
from companion.core.turn.floor import BRUSH_NOTE, HOLD_NOTE
from companion.core.turn.game import game_note
from companion.core.turn.length import LengthTarget, length_target
from companion.core.turn.listening import PROMPT as LISTEN_PROMPT
from companion.core.turn.listening import listening_note, repair_note, rude_note
from companion.core.turn.listening import render_reason as render_listening
from companion.core.turn.ownup import owned_note
from companion.core.turn.questions import question_note
from companion.core.types import (
    Frame,
    Json,
    Speaker,
)
from companion.loops.features import Feature, Lookups, Moment, Offer, Offered, asking
from companion.loops.recall import Recalled, look_up
from companion.prompts import get
from companion.registry import FEATURES

if TYPE_CHECKING:
    from companion.loops.conversation import Conversation
from companion.loops.current import Heard, Turn, decide, mark

log = logging.getLogger("companion.turn")
CHECK_IN_NOTE = get("notes/check-in")
CHECKED_IN = "check-in: asked how they are after a heavy last talk"
CHECK_IN_GAP = timedelta(hours=3)  # away at least this long since their last message
HEAVY_WINDOW = timedelta(hours=12)  # serious messages this close before it make it a heavy talk
SERIOUS = 2
LOOK_SECONDS = 9.0  # every look-up together; past it the reply goes without the late ones


async def look(
    c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None, read: Heard | None
) -> Lookups:
    """Every look-up the reply waits for, run side by side under one deadline (LOOK_SECONDS). Each
    has its own limit too; one still running at the deadline, or one that raised, gives nothing
    this turn and the reply goes ahead. Before, they ran one after another and their limits stacked
    past 15 s (architecture audit, 2026-10-23)."""
    jobs: dict[str, Awaitable[object]] = {
        "recall": _recall(c, t, heard or read),
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
        found={f.name: got[f.name] for f in FEATURES if f.name in got},
    )


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
    recalled = await look_up(
        c.judge,
        c.store.user_beliefs(c.rel),
        heard[0].topic,
        said=c.store.last_support(c.rel),
        now=t.now,
    )
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


def _notes(in_scene: Frame, size: LengthTarget | None) -> list[str]:
    """What it should know about a scene in progress and how long to answer.
    These go in the system block with the memory card: in a user message the model read them as
    something they said."""
    notes = [scene_note(in_scene), size.note if size else None]
    return [n for n in notes if n is not None]


def _length(m: Moment) -> LengthTarget | None:
    """The one length target for this turn, logged with the reason code wrote for it. None on a
    turn the crisis path reads as a risk (ADR 0022)."""
    c, t = m.c, m.t
    severity = m.heard[0].severity if m.heard is not None else None
    size = (
        None
        if m.risk
        else length_target(
            t.text, severity=severity, in_scene=m.in_scene is not Frame.REAL, seed=str(t.turn)
        )
    )
    reason = f"length: under about {size.words} words, {size.why}" if size else "length: no cap"
    if m.risk:
        reason = "length: no cap, the crisis path read a risk"
    decide(
        c, t, "length", {"words": size.words if size else None, "severity": severity}, reason=reason
    )
    return size


@dataclass(frozen=True, slots=True)
class Notes:
    lines: tuple[str, ...]
    after: tuple[Callable[[], None], ...]
    tail: tuple[str, ...] = ()


def _base(m: Moment, _: Offered) -> Offer:
    size = _length(m)
    return Offer(tuple(_notes(m.in_scene, size)))


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


def _game(m: Moment, _: Offered) -> Offer:
    """When they asked it to keep asking them things, a note after the history to ask the next
    one: outside a scene, not on a serious turn and not on one the crisis path reads as a risk."""
    serious = m.risk or (m.heard is not None and m.heard[0].severity >= SERIOUS)
    if m.in_scene is not Frame.REAL or serious:
        return Offer()
    note = game_note(m.t.prior, m.t.text, m.t.now)
    return Offer(tail=(note,) if note else ())


def _questions(m: Moment, so_far: Offered) -> Offer:
    """When its last replies were all questions, a note to ask nothing this time: outside a scene,
    not on a serious turn, and not when another note asks them something. After the history."""
    serious = m.heard is not None and m.heard[0].severity >= SERIOUS
    if m.in_scene is not Frame.REAL or serious or asking(so_far):
        return Offer()
    replies = [u.text for u in m.t.prior if u.speaker is Speaker.COMPANION]
    note = question_note(replies)
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


def _feature_note(f: Feature) -> Callable[[Moment, Offered], Offer]:
    note = f.note
    assert note is not None

    def source(m: Moment, so_far: Offered) -> Offer:
        return note(m, m.looked.found.get(f.name), so_far)

    return source


# The notes that are not features' own, by name.
_LOCAL: dict[str, Callable[[Moment, Offered], Offer]] = {
    "base": _base,
    "listening": _listening,
    "rude": _rude,
    "repair": _repair,
    "owned": _owned,
    "recall": _recalled,
    "check-in": _check_in,
    "hold": _hold,
    "brush-off": _brush,
    "game": _game,
    "questions": _questions,
}

# Every note, in the order it reaches the system block. A source sees what the ones before it
# offered: a plan or a move on waits while their name is asked, a move on knows a plan was offered.
ORDER: tuple[str, ...] = (
    "moves",
    "base",
    "listening",
    "rude",
    "repair",
    "owned",
    "recall",
    "relevant",
    "recent",
    "check-in",
    "mood",
    "hold",
    "brush-off",
    "name",
    "memory map",
    "loop",
    "topic",
    "guess",
    "lore",
    "mark",
    "reminder",
    "crisis",
    "game",
    "calendar",
    "questions",
)


def _sources() -> tuple[tuple[str, Callable[[Moment, Offered], Offer]], ...]:
    """The notes in ORDER, local or a feature's, checked when the module loads: a name with no note,
    or a feature's note left out or placed twice, stops the bot at start rather than silently."""
    noted = {f.name: f for f in FEATURES if f.note is not None}
    missing = [n for n in ORDER if n not in _LOCAL and n not in noted]
    unplaced = [n for n in noted if ORDER.count(n) != 1] + [n for n in _LOCAL if n not in ORDER]
    if missing or unplaced or len(set(ORDER)) != len(ORDER):
        msg = f"notes order: no source for {missing}, not placed once: {unplaced}"
        raise RuntimeError(msg)
    return tuple((n, _LOCAL[n] if n in _LOCAL else _feature_note(noted[n])) for n in ORDER)


SOURCES = _sources()


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
