"""The notes a turn adds to the system block, and the look-ups they wait for."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import timedelta
from typing import TYPE_CHECKING

from companion.core.frames import (
    scene_note,
)
from companion.core.turn.floor import BRUSH_NOTE, HOLD_NOTE
from companion.core.turn.listening import (
    LISTENING_KEY,
    listening_labels,
    listening_note,
    logged_heavy,
    repair_note,
    rude_note,
)
from companion.core.turn.listening import PROMPT as LISTEN_PROMPT
from companion.core.turn.listening import render_reason as render_listening
from companion.core.turn.mentions import ASKED_HOW_THEY_ARE
from companion.core.turn.ownup import owned_note
from companion.core.turn.quoted import quoted_note
from companion.core.types import Speaker
from companion.kit.features import (
    LOOKS_TOGETHER_SECONDS,
    ROOM_READS,
    Feature,
    Lookups,
    Moment,
    NoteName,
    Offer,
    Offered,
)
from companion.prompts import get
from companion.registry import FEATURES
from companion.turn.mention import mention_note

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime
from companion.kit.current import Heard, Turn, decide

log = logging.getLogger("companion.turn")
HOW_ARE_YOU_NOTE = get("notes/check-in")
HOW_ARE_YOU_GAP = timedelta(hours=3)  # away at least this long since their last message
HEAVY_WINDOW = timedelta(hours=12)  # serious messages this close before it make it a heavy talk


async def look(m: Moment, read: Heard | None) -> Lookups:
    """Every look-up the reply waits for, run side by side under one deadline
    (LOOKS_TOGETHER_SECONDS). Each has its own limit too, which `check_look_seconds` keeps under the
    deadline; one still running at the deadline, or one that raised,
    gives nothing this turn and the reply goes ahead. In a scene a look-up that asks for it
    (`Feature.scene_read`) gets the route's read, since the listening judge does not run there."""
    jobs: dict[str, Awaitable[object]] = {
        f.name: f.look(replace(m, heard=m.heard or read) if f.scene_read else m)
        for f in FEATURES
        if f.look is not None and f.can_read(m.c)
    }
    if not jobs:
        return Lookups()
    tasks = {name: asyncio.ensure_future(job) for name, job in jobs.items()}
    _, late = await asyncio.wait(tasks.values(), timeout=LOOKS_TOGETHER_SECONDS)
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
    return Lookups(found={f.name: got[f.name] for f in FEATURES if f.name in got})


def _listening_note(c: Runtime, t: Turn, heard: Heard | None) -> str | None:
    """The line for the system block, with the decision logged from the labels."""
    if heard is None:
        return None
    judged = heard.read
    replies = [u.text for u in t.prior if u.speaker is Speaker.COMPANION]
    note = listening_note(judged, replies, seed=t.turn)
    decide(
        c,
        t,
        LISTENING_KEY,
        heard.detail(LISTEN_PROMPT.ref, labels=listening_labels(judged)),
        reason=render_listening(judged, note),
    )
    return note


@dataclass(frozen=True, slots=True)
class Notes:
    lines: tuple[str, ...]
    after: tuple[Callable[[], None], ...]
    tail: tuple[str, ...] = ()


def _base(m: Moment, _: Offered) -> Offer:
    """What it should know about a scene in progress. In the system block with the memory card: in
    a user message the model read it as something they said."""
    note = scene_note(m.in_scene)
    return Offer((note,) if note else ())


def _replied_to(m: Moment, _: Offered) -> Offer:
    """The message they used reply on, quoted, so it knows which one they answer."""
    quoted = m.t.quoted
    note = quoted_note(quoted)
    if quoted is None or note is None:
        return Offer()
    decide(
        m.c,
        m.t,
        "replied-to",
        {"speaker": quoted.speaker.value, "text": quoted.text},
        reason=f"replied-to: they replied to a message of the {quoted.speaker.value}'s",
    )
    return Offer((note,))


def _listening(m: Moment, _: Offered) -> Offer:
    note = _listening_note(m.c, m.t, m.heard)
    return Offer((note,) if note else ())


def _rude(m: Moment, _: Offered) -> Offer:
    note = rude_note(m.heard.read) if m.heard is not None else None
    return Offer((note,) if note else ())


def _repair(m: Moment, _: Offered) -> Offer:
    note = repair_note(m.heard.read) if m.heard is not None else None
    return Offer((note,) if note else ())


def _owned(m: Moment, so_far: Offered) -> Offer:
    """When one of its last replies owned a slip, a note not to own more: outside a scene, and not
    when they say it got them wrong this turn (the repair note's). Sent after the history: in the
    system block it moved nothing (measured 2026-10-22)."""
    if m.pretend:
        return Offer()
    replies = [u.text for u in m.t.prior if u.speaker is Speaker.COMPANION]
    note = owned_note(replies, repairing=bool(so_far[NoteName.REPAIR].lines))
    return Offer(tail=(note,) if note else ())


def _how_are_you(m: Moment, _: Offered) -> Offer:
    """When they come back after a gap and the talk before it was heavy (a serious message in its
    last hours), one note to ask gently how they are, once per heavy talk."""
    c, t = m.c, m.t
    if m.unread_or_heavy or m.pretend:
        return Offer()
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    if not theirs or t.now - theirs[-1].at < HOW_ARE_YOU_GAP:
        return Offer()
    last = theirs[-1].at
    if c.store.decided_since(c.rel, ASKED_HOW_THEY_ARE, last):
        return Offer()
    recent = [u.turn_id for u in theirs if last - u.at <= HEAVY_WINDOW]
    heavy = any(
        logged_heavy(d.detail)
        for turn in recent
        for d in c.store.decisions_for_turn(c.rel, turn)
        if d.has_key(LISTENING_KEY)
    )
    if not heavy:
        return Offer()
    return Offer((HOW_ARE_YOU_NOTE.text,), (lambda: decide(c, t, ASKED_HOW_THEY_ARE),), asks=True)


def _hold(m: Moment, _: Offered) -> Offer:
    return Offer((HOLD_NOTE.text,) if m.held else ())


def _brush(m: Moment, _: Offered) -> Offer:
    return Offer((BRUSH_NOTE.text,) if m.brushed else ())


def _feature_note(f: Feature) -> Callable[[Moment, Offered], Offer]:
    def source(m: Moment, so_far: Offered) -> Offer:
        return f.offer(m, m.looked.found.get(f.name), so_far)

    return source


# The earlier notes a local note reads by name (a feature's note declares `Feature.reads`).
_LOCAL_READS: dict[str, tuple[str, ...]] = {
    NoteName.OWNED: (NoteName.REPAIR,),
    NoteName.MENTION: ROOM_READS,
}

# The notes that are not features' own, by name.
_LOCAL: dict[str, Callable[[Moment, Offered], Offer]] = {
    NoteName.BASE: _base,
    NoteName.REPLIED_TO: _replied_to,
    NoteName.LISTENING: _listening,
    NoteName.RUDE: _rude,
    NoteName.REPAIR: _repair,
    NoteName.OWNED: _owned,
    NoteName.HOW_ARE_YOU: _how_are_you,
    NoteName.HOLD: _hold,
    NoteName.BRUSH_OFF: _brush,
    NoteName.MENTION: mention_note,
}

# Every note, in the order it reaches the system block. A source sees what the ones before it
# offered: what it brings up on its own (`mention`) waits while their name is asked or any note
# before it asks them something, and a move on knows a plan was brought up.
ORDER: tuple[str, ...] = (
    NoteName.TICS,
    NoteName.BASE,
    NoteName.LENGTH,
    NoteName.REPLIED_TO,
    NoteName.LISTENING,
    NoteName.RUDE,
    NoteName.REPAIR,
    NoteName.OWNED,
    NoteName.RECALL,
    NoteName.NOW,
    NoteName.RELEVANT,
    NoteName.RECENT,
    NoteName.HOW_ARE_YOU,
    NoteName.MOOD,
    NoteName.HOLD,
    NoteName.BRUSH_OFF,
    NoteName.NAME,
    NoteName.MEMORY_MAP,
    NoteName.GUESS,
    NoteName.REMINDER,
    NoteName.CRISIS,
    NoteName.GAME,
    NoteName.MENTION,
    NoteName.TOPIC,
    NoteName.LORE,
    NoteName.MARK,
    NoteName.QUESTIONS,
)


type Source = tuple[str, Callable[[Moment, Offered], Offer], tuple[str, ...]]  # name, note, reads


def sources() -> tuple[Source, ...]:
    """The notes in ORDER, local or a feature's, checked when the module loads: a name with no note,
    or a feature's note left out or placed twice, or a note that reads one that does not come
    before it, stops the bot at start rather than silently."""
    noted = {f.name: f for f in FEATURES if f.note is not None}
    missing = [n for n in ORDER if n not in _LOCAL and n not in noted]
    unplaced = [n for n in noted if ORDER.count(n) != 1] + [n for n in _LOCAL if n not in ORDER]
    if missing or unplaced or len(set(ORDER)) != len(ORDER):
        msg = f"notes order: no source for {missing}, not placed once: {unplaced}"
        raise RuntimeError(msg)
    sources: list[Source] = [
        (n, _LOCAL[n], _LOCAL_READS.get(n, ()))
        if n in _LOCAL
        else (n, _feature_note(noted[n]), noted[n].reads)
        for n in ORDER
    ]
    late = [
        f"{n} reads {r}"
        for n, _, reads in sources
        for r in reads
        if r not in ORDER[: ORDER.index(n)]
    ]
    if late:
        msg = f"notes order: a note reads one that does not come before it: {late}"
        raise RuntimeError(msg)
    return tuple(sources)


def check_look_seconds() -> None:
    """Every look-up states how long it waits (`Feature.look_seconds`), and none waits past the
    shared deadline, where its own limit would never fire. Checked when the module loads."""
    bad = [
        f.name
        for f in FEATURES
        if f.look is not None
        and (f.look_seconds is None or f.look_seconds > LOOKS_TOGETHER_SECONDS)
    ]
    if bad:
        msg = f"look-ups with no limit, or one past {LOOKS_TOGETHER_SECONDS} s: {bad}"
        raise RuntimeError(msg)


check_look_seconds()
SOURCES = sources()


def notes_for(m: Moment) -> Notes:
    """Every note for this turn, in order, and the writes to make once the reply is stored."""
    offered: dict[str, Offer] = {}
    for name, source, reads in SOURCES:
        offered[name] = source(m, Offered(offered, reads))
    return Notes(
        tuple(line for o in offered.values() for line in o.lines),
        tuple(f for o in offered.values() for f in o.after),
        tuple(line for o in offered.values() for line in o.tail),
    )
