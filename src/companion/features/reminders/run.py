"""Reminders they ask for (J50): read on the turn they ask, sent when due.

The read runs before the reply only when code sees reminder words or the companion just asked when;
code works out the time and adds one note, so the reply confirms the time or asks about it. A due
reminder is claimed once, written by the talker in its own voice, checked by code, and sent. While a
pretend scene is in progress it waits until the scene ends.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from typing import TYPE_CHECKING

from companion.core.clock import named_zone, now_line
from companion.core.extractor import Extractor
from companion.core.frames import scene_frame
from companion.core.history import HISTORY_LIMIT, to_messages
from companion.core.prompt.request import TalkerRequest
from companion.core.prompt.sections import tagged
from companion.core.recheck import code_checks
from companion.core.types import (
    Frame,
    Json,
    SessionId,
    Speaker,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.reminders.logic import (
    ASKED_WHEN,
    GRACE,
    ONE_OFF,
    PROMPT,
    SCHEMA,
    SEND,
    Ask,
    Slots,
    ask_note,
    cancelled_note,
    likely,
    matching,
    parse,
    plain,
    read_prompt,
    resolve,
    send_instruction,
    set_note,
    spoken,
    trusted,
)
from companion.features.reminders.store import Reminder
from companion.loops.ask import Judge, ask
from companion.loops.current import Heard, Turn, mark
from companion.loops.features import Feature, Offer, Offered
from companion.loops.record import Recorder
from companion.loops.spendcap import over_cap

if TYPE_CHECKING:
    from companion.loops.conversation import Conversation
    from companion.loops.features import Moment

log = logging.getLogger("companion.reminders")
TIMEOUT_SECONDS = 8.0
READER = Judge(
    "reminders",
    PROMPT,
    SCHEMA,
    parse,
    timeout=TIMEOUT_SECONDS,
    unread="no reminder this turn",
    trust_fallback=False,
)
LATE = timedelta(minutes=5)  # sent later than this after its time, it is marked late
SET, ASKED, CANCELLED = "reminders: set", ASKED_WHEN, "reminders: cancelled"


@dataclass(frozen=True, slots=True)
class Read:
    """What a turn's reading of a reminder request came to: the note for the reply and the
    decision to log."""

    note: str
    reason: str
    detail: dict[str, Json]


async def read_slots(
    judge: Extractor, prior: Sequence[Utterance], said: str, now: datetime, tz: tzinfo
) -> Slots | None:
    got = await ask(judge, READER, read_prompt(prior, said, now, tz))
    return None if got is None else trusted(got.value, said)


def act(  # noqa: PLR0913, PLR0917
    c: Conversation,
    s: Slots,
    said: str,
    turn: TurnId,
    now: datetime,
    tz: tzinfo,
) -> Read | None:
    """Store or cancel what they asked for, and the note that tells the reply what happened."""
    if s.ask is Ask.CANCEL:
        pending = [r for r in c.store.reminders(c.rel) if r.state == "pending"]
        hit = matching([(r.id, r.thing) for r in pending], s.thing)
        if not hit:
            return None
        for rid in hit:
            c.store.reminder_event(rid, "cancelled", "they asked to drop it", now)
        things = [r.thing for r in pending if r.id in hit]
        return Read(cancelled_note(" and ".join(things)), CANCELLED, {"reminders": list[Json](hit)})
    if s.ask is not Ask.SET or not s.thing:
        return None
    if s.repeats:
        return Read(ask_note(s.thing, ONE_OFF), ASKED, {"why": "repeating"})
    when = resolve(s, now, tz)
    if when.at is None:
        return Read(ask_note(s.thing, when.unclear), ASKED, {"why": when.unclear})
    local = when.at.astimezone(tz)
    r = Reminder(
        uuid.uuid4().hex,
        c.rel,
        s.kind,
        s.thing,
        said,
        when.at,
        local.strftime("%Y-%m-%d %H:%M"),
        str(tz),
        turn,
        now,
    )
    c.store.add_reminder(r)
    told = spoken(when.at, now, tz, loose=when.loose)
    return Read(
        set_note(s.thing, told, defaulted=when.defaulted),
        SET,
        {"reminder": r.id, "kind": s.kind.value, "due": told, "defaulted": when.defaulted},
    )


def log_decision(  # noqa: PLR0913, PLR0917
    c: Conversation,
    session: SessionId,
    turn: TurnId,
    reason: str,
    now: datetime,
    detail: dict[str, Json] | None = None,
) -> None:
    Recorder(c.store, c.rel, session, turn, TraceId(turn), now).decide(reason, detail)


async def _write(
    c: Conversation, r: Reminder, prior: Sequence[Utterance], now: datetime
) -> tuple[str, str]:
    """The message and who wrote it: the talker in its own voice, drawn once more when a code check
    fails; their words, marked, when the talker cannot be asked or says nothing."""
    if over_cap(c.store, c.rel, c.daily_cap_usd, now) is not None:
        return plain(r.kind, r.thing), "code: over the daily cap"
    theirs = [u for u in prior if u.speaker is Speaker.USER]
    request = TalkerRequest(
        c.prefix,
        tuple(to_messages(prior)),
        card=tagged(now_line(now, theirs[-1].at if theirs else None), memory=False),
        tail=send_instruction(r.kind, r.thing),
    )
    text, model = "", ""
    for _ in range(2):
        try:
            reply = await c.talker.reply(request)
        except Exception:
            log.warning("the talker could not write a reminder; sending it plainly", exc_info=True)
            break
        text, model = reply.text.strip(), reply.model
        if text and not code_checks(text):
            break
    return (text, model) if text else (plain(r.kind, r.thing), "code: the talker said nothing")


async def deliver_due(
    c: Conversation,
    send: Callable[[str], Awaitable[None]],
    session: SessionId,
    now: datetime,
    started: datetime,
) -> int:
    """Send every reminder that is due, once. One that fell due while the bot was not running and is
    now more than GRACE late is let go; one held by a scene waits for the scene to end. Returns how
    many went out."""
    due = [r for r in c.store.reminders(c.rel) if r.state == "pending" and r.due_at <= now]
    sent = 0
    for r in due:
        turn = TurnId(uuid.uuid4().hex)
        if r.due_at < started and now - r.due_at > GRACE:
            c.store.reminder_event(r.id, "expired", "the bot was not running when it was due", now)
            log_decision(
                c,
                session,
                turn,
                "reminders: let go, missed while not running",
                now,
                {"reminder": r.id},
            )
            continue
        prior = c.store.history_before(c.rel, now, HISTORY_LIMIT)
        if scene_frame(prior, now) is not Frame.REAL:
            log.debug("reminder %s held: a scene is in progress", r.id[:8])
            continue
        if not c.store.claim_reminder(r.id, now):
            continue
        text, by = await _write(c, r, prior, now)
        try:
            await send(text)
        except Exception:
            log.warning("a reminder could not be sent; it will be tried again", exc_info=True)
            c.store.reminder_event(r.id, "pending", "sending failed, tried again next time", now)
            continue
        c.store.append_utterance(
            Utterance(
                UtteranceId(uuid.uuid4().hex),
                c.rel,
                session,
                turn,
                Speaker.COMPANION,
                text,
                Frame.REAL,
                "telegram",
                now,
            )
        )
        late = now - r.due_at > LATE
        c.store.reminder_event(r.id, "late" if late else "sent", f"sent by {by}", now)
        log_decision(
            c,
            session,
            turn,
            f"reminders: sent{' late' if late else ''}",
            now,
            {"reminder": r.id, "kind": r.kind.value, "by": by, "prompt": SEND.ref},
        )
        log.info("reminder %s sent%s: %s", r.id[:8], " late" if late else "", text)
        sent += 1
    return sent


async def reminder_for_turn(
    c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None
) -> str | None:
    """When they ask to be reminded or checked on, or answer its asking when (J50): read the words,
    let code set the time, and say in a note what happened."""
    del in_scene, heard
    last = next((u for u in reversed(t.prior) if u.speaker is Speaker.COMPANION), None)
    asked = last is not None and any(
        d.has_key(ASKED) for d in c.store.decisions_for_turn(c.rel, last.turn_id)
    )
    if c.judge is None or not c.reminders or not likely(t.text, asked_when=asked):
        return None
    mark(t, "reminder judge")
    zone = named_zone()
    slots = await read_slots(c.judge, t.prior, t.text, t.now, zone)
    done = act(c, slots, t.text, t.turn, t.now, zone) if slots is not None else None
    if done is None:
        return None
    log_decision(c, t.session, t.turn, done.reason, t.now, done.detail | {"prompt": PROMPT.ref})
    return done.note


def reminder_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """The note saying a reminder was set, cancelled, or what to ask."""
    del m, so_far
    return Offer((found,) if isinstance(found, str) and found else ())


REMINDERS = Feature("reminder", look=reminder_for_turn, note=reminder_offer)
