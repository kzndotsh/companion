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
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, tzinfo
from typing import TYPE_CHECKING

from companion.core.clock import named_zone, now_line
from companion.core.extractor import StructuredModel
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
    CONTEXT,
    GRACE,
    PROMPT,
    SCHEMA,
    Ask,
    Reminder,
    Series,
    Slots,
    Standing,
    ask_note,
    asked_for,
    cancelled_note,
    likely,
    matching,
    parse,
    plain,
    read_prompt,
    resolve,
    send_instruction,
    sent_with,
    set_note,
    spoken,
    trusted,
)
from companion.features.reminders.series import (
    LOOK_BACK,
    Planned,
    Step,
    every_words,
    first_words,
    how_often,
    repeat_note,
    repeat_of,
    skip_reason,
    tend,
)
from companion.kit.ask import Judge, ask
from companion.kit.current import Heard, Turn, mark
from companion.kit.features import Feature, Offer, Offered
from companion.kit.record import Recorder
from companion.kit.spendcap import over_cap

if TYPE_CHECKING:
    from companion.kit.features import Moment
    from companion.kit.runtime import Runtime
    from companion.store.sqlite.store import Store

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
# A send takes under a minute, a minute more if Telegram asks to wait. One still claimed after this
# was cut off by a crash or a restart mid-send; left claimed it would block its series for good.
STUCK = timedelta(minutes=10)
SET, ASKED, CANCELLED = "reminders: set", ASKED_WHEN, "reminders: cancelled"
SKIPPED, PAUSED, RESUMED = "reminders: skipped", "reminders: paused", "reminders: resumed"
STUCK_GONE = "reminders: let go, cut off mid-send"


@dataclass(frozen=True, slots=True)
class Read:
    """What a turn's reading of a reminder request came to: the note for the reply and the
    decision to log."""

    note: str
    reason: str
    detail: dict[str, Json]
    asks: bool = False  # the note asks them when


async def read_slots(
    judge: StructuredModel, prior: Sequence[Utterance], said: str, now: datetime, tz: tzinfo
) -> Slots | None:
    got = await ask(judge, READER, read_prompt(prior, said, now, tz))
    return None if got is None else trusted(got.value, said)


def schedule(c: Runtime, series: Series, now: datetime, tz: tzinfo) -> Step:
    """Bring a series up to date: record a pause or a resume, and make its next occurrence when the
    one before has ended. Safe to run any number of times: the store keeps one of each number."""
    occurrences = [r for r in c.store.reminders(c.rel) if r.series_id == series.id]
    step = tend(series, occurrences, c.store.their_times(c.rel, now - LOOK_BACK), now, tz)
    if step.state is not None:
        c.store.series_event(series.id, step.state, step.reason, now)
    if step.due is None:
        return step
    made = c.store.add_occurrence(
        Reminder(
            uuid.uuid4().hex,
            c.rel,
            series.kind,
            series.thing,
            series.quote,
            step.due,
            step.due.astimezone(tz).strftime("%Y-%m-%d %H:%M"),
            str(tz),
            series.turn_id,
            now,
            series_id=series.id,
            seq=step.seq,
        )
    )
    return step if made else replace(step, due=None)


def stop(store: Store, series: Series, reason: str, now: datetime) -> None:
    """Stop a series and drop its pending occurrence. Stopped first, so a tick in between makes no
    next one."""
    store.series_event(series.id, Standing.STOPPED, reason, now)
    for r in store.reminders(series.relationship_id):
        if r.series_id == series.id and r.state == "pending":
            store.reminder_event(r.id, "cancelled", reason, now)


def _cancel(c: Runtime, s: Slots, now: datetime) -> Read | None:
    """Drop the pending one-offs and stop the series their words name (or the only one)."""
    pending = [r for r in c.store.reminders(c.rel) if r.state == "pending" and r.series_id is None]
    live = [x for x in c.store.series(c.rel) if x.state is not Standing.STOPPED]
    hit = set(
        matching([(r.id, r.thing) for r in pending] + [(x.id, x.thing) for x in live], s.thing)
    )
    if not hit:
        return None
    dropped = [r for r in pending if r.id in hit]
    stopped = [x for x in live if x.id in hit]
    for r in dropped:
        c.store.reminder_event(r.id, "cancelled", "they asked to drop it", now)
    for x in stopped:
        stop(c.store, x, "they asked to stop it", now)
    what = [asked_for(r.kind, r.thing) for r in dropped] + [
        f"{asked_for(x.kind, x.thing)} {how_often(x.repeat)}" for x in stopped
    ]
    detail: dict[str, Json] = {
        "reminders": [r.id for r in dropped],
        "series": [x.id for x in stopped],
    }
    return Read(cancelled_note(" and ".join(what)), CANCELLED, detail)


def _started(c: Runtime, series: Series, planned: Planned, now: datetime, tz: tzinfo) -> Read:
    c.store.add_series(series)
    due = schedule(c, series, now, tz).due or now  # a new series always has a first one
    first = first_words(planned.repeat, due, now, tz)
    return Read(
        repeat_note(series.kind, series.thing, planned, first),
        SET,
        {
            "series": series.id,
            "kind": series.kind.value,
            "every": every_words(planned.repeat),
            "first": first,
            "defaulted": planned.defaulted,
        },
    )


def act(  # noqa: PLR0913, PLR0917
    c: Runtime,
    s: Slots,
    said: str,
    turn: TurnId,
    now: datetime,
    tz: tzinfo,
) -> Read | None:
    """Store or cancel what they asked for, and the note that tells the reply what happened."""
    if s.ask is Ask.CANCEL:
        return _cancel(c, s, now)
    if s.ask is not Ask.SET or not s.thing:
        return None
    if s.repeats:
        planned = repeat_of(s, now, tz)
        if isinstance(planned, str):
            why: dict[str, Json] = {"why": planned, "repeats": True}
            return Read(ask_note(s.kind, s.thing, planned), ASKED, why, asks=True)
        made = Series(
            uuid.uuid4().hex, c.rel, s.kind, s.thing, said, planned.repeat, str(tz), turn, now
        )
        return _started(c, made, planned, now, tz)
    when = resolve(s, now, tz)
    if when.at is None:
        return Read(
            ask_note(s.kind, s.thing, when.unclear), ASKED, {"why": when.unclear}, asks=True
        )
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
        set_note(s.kind, s.thing, told, defaulted=when.defaulted),
        SET,
        {"reminder": r.id, "kind": s.kind.value, "due": told, "defaulted": when.defaulted},
    )


def log_decision(  # noqa: PLR0913, PLR0917
    c: Runtime,
    session: SessionId,
    turn: TurnId,
    reason: str,
    now: datetime,
    detail: dict[str, Json] | None = None,
) -> None:
    Recorder(c.store, c.rel, session, turn, TraceId(turn), now).decide(reason, detail)


async def _write(
    c: Runtime, r: Reminder, prior: Sequence[Utterance], now: datetime
) -> tuple[str, str]:
    """The message and who wrote it: the talker in its own voice, drawn once more when a code check
    fails; their words, marked, when the talker cannot be asked or says nothing."""
    if over_cap(c.store, c.rel, c.daily_cap_usd, now) is not None:
        return plain(r.kind, r.thing), "code: over the daily cap"
    theirs = [u for u in prior if u.speaker is Speaker.USER]
    request = TalkerRequest(
        c.prefix,
        tuple(to_messages(prior, now)),
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


async def deliver_due(  # noqa: PLR0913
    c: Runtime,
    send: Callable[[str], Awaitable[object]],
    session: SessionId,
    now: datetime,
    started: datetime,
    *,
    channel: str,
) -> int:
    """Send every reminder that is due, once, over `send`, and store it as said on `channel` (the
    surface it went out on). One left claimed by a send that was cut off is let go, never resent.
    One that fell due while the bot was not running and is now more than GRACE late is let go; a
    greeting they already wrote first is skipped; one held by a scene waits for the scene to end.
    Then every series is brought up to date. Returns how many went out."""
    held = c.store.reminders(c.rel)
    for r in held:
        if r.state == "claimed" and r.state_at is not None and now - r.state_at > STUCK:
            why = "claimed and never finished, cut off mid-send; whether it arrived is unknown"
            c.store.reminder_event(r.id, "expired", why + ", so it is not sent again", now)
            detail_stuck: dict[str, Json] = {"reminder": r.id, "series": r.series_id}
            log_decision(c, session, TurnId(uuid.uuid4().hex), STUCK_GONE, now, detail_stuck)
    due = [r for r in held if r.state == "pending" and r.due_at <= now]
    every, zone = {x.id: x for x in c.store.series(c.rel)}, named_zone()
    theirs = c.store.their_times(c.rel, now - LOOK_BACK)
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
        series = every.get(r.series_id or "")
        why = None if series is None else skip_reason(series, r.due_at, theirs, now, zone)
        if why is not None:
            if c.store.claim_reminder(r.id, now):
                c.store.reminder_event(r.id, "skipped", why, now)
                detail: dict[str, Json] = {"reminder": r.id, "series": r.series_id, "why": why}
                log_decision(c, session, turn, SKIPPED, now, detail)
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
                channel,
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
            {"reminder": r.id, "kind": r.kind.value, "by": by, "prompt": sent_with(r.kind)},
        )
        log.info("reminder %s sent%s: %s", r.id[:8], " late" if late else "", text)
        sent += 1
    for series in c.store.series(c.rel):  # read again: a turn may have stopped one while it sent
        if series.state is not Standing.STOPPED:
            _tend(c, series, session, now, zone)
    return sent


def _tend(c: Runtime, series: Series, session: SessionId, now: datetime, tz: tzinfo) -> None:
    step = schedule(c, series, now, tz)
    if step.state is not None:
        key = PAUSED if step.state is Standing.PAUSED else RESUMED
        detail: dict[str, Json] = {"series": series.id, "why": step.reason}
        log_decision(c, session, TurnId(uuid.uuid4().hex), key, now, detail)


def unhandled(c: Runtime, prior: Sequence[Utterance]) -> list[Utterance]:
    """The conversation the reader sees, without their earlier messages that already set or
    cancelled a reminder. Shown one, the reader took a comment on that reminder ("see, you can do
    reminders") as the same request again, 30 times in 30 (2026-10-26)."""
    return [
        u
        for u in prior[-CONTEXT:]
        if u.speaker is not Speaker.USER
        or not any(
            d.has_key(SET) or d.has_key(CANCELLED)
            for d in c.store.decisions_for_turn(c.rel, u.turn_id)
        )
    ]


async def reminder_for_turn(
    c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None
) -> Read | None:
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
    slots = await read_slots(c.judge, unhandled(c, t.prior), t.text, t.now, zone)
    done = act(c, slots, t.text, t.turn, t.now, zone) if slots is not None else None
    if done is None:
        return None
    log_decision(c, t.session, t.turn, done.reason, t.now, done.detail | {"prompt": PROMPT.ref})
    return done


def reminder_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """The note saying a reminder was set, cancelled, or what to ask."""
    del m, so_far
    if not isinstance(found, Read) or not found.note:
        return Offer()
    return Offer((found.note,), asks=found.asks)


REMINDERS = Feature("reminder", look=reminder_for_turn, note=reminder_offer)
