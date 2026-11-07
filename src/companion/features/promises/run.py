"""Reading the companion's own messages for the promises it made (J12), and checking each reply
against them. The read runs in the open-loop pass's batch and keeps its bookmark, so a failed call
is read again. Shadow only: nothing reaches the talker."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime, tzinfo

from companion.core import switch
from companion.core.beliefs.extract import build_user_prompt
from companion.core.extractor import StructuredModel
from companion.core.ids import new_id
from companion.core.types import Json, Speaker, Utterance, UtteranceId
from companion.features.promises.logic import (
    CHECK,
    CHECK_SCHEMA,
    PROMPT,
    RECENT,
    SCHEMA,
    SYSTEM,
    agreed,
    check_input,
    in_force,
    parse,
    read_check,
    to_promise,
)
from companion.features.promises.store import Promises
from companion.kit.ask import Judge, ask
from companion.kit.current import decide
from companion.kit.features import Feature, Log, Moment, OwnReader, Passing
from companion.kit.reads import read_times
from companion.lib.vote import READS
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.promises")


async def read_promises(  # noqa: PLR0913, PLR0917
    store: Store,
    extractor: StructuredModel,
    window: Mapping[str, Utterance],
    targets: set[UtteranceId],
    when: tuple[datetime, tzinfo],
    note: Log,
) -> float | None:
    """Record the promises in its targeted messages. The cost, or None when the call failed so the
    batch is read again."""
    now, tz = when
    got = await read_times(
        extractor,
        SYSTEM,
        build_user_prompt(window, targets, {}, tz),
        SCHEMA,
        parse,
        spend="promises",
        timeout=90.0,  # a batch of the companion's messages, three reads at once
    )
    reads = [r for r in got.values if r is not None]
    if len(reads) < READS:
        log.warning("promise read failed or was malformed; the batch is kept for another try")
        return None
    proposed, disputed = agreed(reads)
    for p in disputed:
        note("promise dropped: the reads did not agree", {"quote": p.quote, "claim": p.claim})
    rel = next(iter(window.values())).relationship_id
    known = {
        (r.promise.utterance_id, r.promise.quote.lower())
        for r in store.part(Promises).recorded(rel)
    }
    for p in proposed:
        outcome = to_promise(p, window, new_id())
        if isinstance(outcome, str):
            note(f"promise dropped: {outcome}", {"quote": p.quote, "claim": p.claim})
            continue
        if (outcome.utterance_id, outcome.quote.lower()) in known:
            continue
        store.part(Promises).add(outcome, model=got.model, prompt=PROMPT.ref, at=now)
        known.add((outcome.utterance_id, outcome.quote.lower()))
        note(
            "promise recorded from its own words (shadow)",
            {
                "promise_id": outcome.id,
                "kind": outcome.kind,
                "claim": outcome.claim,
                "quote": outcome.quote,
                "avoid": outcome.avoid,
                "prompt": PROMPT.ref,
            },
        )
    return got.cost_usd


CHECK_JUDGE = Judge(
    "promise-check", CHECK, CHECK_SCHEMA, read_check, timeout=20.0, unread="no promise check"
)
WOULD_REDRAW = "promise check (shadow): would redraw"
KEPT = "promise check: kept"
WOULD_RETIRE = "promise check (shadow): would retire"


async def check_reply(m: Moment, said: Utterance, sent: str | None) -> None:
    """Once the reply is stored, read it against its current promises (the dispatcher runs the step
    beside the turn, so the next message never waits on it). Shadow: it logs what it would redraw
    and retire."""
    del said
    c, t = m.c, m.t
    if not sent:
        return
    current = [
        r.promise
        for r in c.store.part(Promises).recorded(c.rel)
        if r.mark is None and in_force(r.promise, t.now)
    ]
    if not current:
        return
    recent = [(u.speaker, u.text) for u in t.prior[-(RECENT - 1) :]] + [(Speaker.USER, t.text)]
    text, labels = check_input(current, recent, sent)
    got = await ask(m.judge, CHECK_JUDGE, text)
    if got is None:
        return
    found = got.value
    shown: dict[str, Json] = {k: p.claim for k, p in labels.items()}
    detail: dict[str, Json] = {"promises": shown, "why": found.why, "prompt": got.ref}
    for label in found.released:
        if label in labels:
            p = labels[label]
            reason = f"{WOULD_RETIRE}: they released it or its time is over: {p.claim}"
            decide(c, t, WOULD_RETIRE, {**detail, "promise_id": p.id}, reason=reason)
    broken = labels.get(found.broken or "")
    if broken is None:
        decide(c, t, KEPT, detail, reason=f"{KEPT}: {len(labels)} promises read")
        return
    reason = f"{WOULD_REDRAW}: it breaks {broken.claim}"
    decide(c, t, WOULD_REDRAW, {**detail, "promise_id": broken.id}, reason=reason)


def promise_reader(p: Passing) -> OwnReader | None:
    """The read of its own messages that rides the open-loop batch, none while the switch is off."""
    return read_promises if p.on(switch.PROMISES) else None


PROMISE_CHECK = Feature(
    "promise check",
    after_turn=check_reply,
    own_loop=promise_reader,
    switch=switch.PROMISES,
    needs_judge=True,
)
