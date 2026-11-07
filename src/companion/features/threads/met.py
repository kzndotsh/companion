"""How they met what the companion brought up (ADR 0023): once the turn is stored, when its last
message brought something up (a plan, a day, or the how-are-you question), their message is read
once for how it was met, for the pace the picker (`turn/mention.py`) learns in shadow."""

from __future__ import annotations

from companion.core.turn.mentions import (
    ASKED_HOW_THEY_ARE,
    MENTION_KEYS,
    MET,
    MET_PROMPT,
    MET_SCHEMA,
    met_prompt,
    parse_met,
)
from companion.core.types import Json, Speaker, Utterance
from companion.kit.ask import Judge, ask
from companion.kit.current import decide
from companion.kit.features import Moment

MET_JUDGE = Judge("thread-met", MET_PROMPT, MET_SCHEMA, parse_met, timeout=8.0, unread="no label")


async def read_met(m: Moment, said: Utterance, sent: str | None) -> None:
    """Read how their message met what the last reply brought up, once, and log it. It only feeds
    the learned pace, in shadow, so the dispatcher runs it beside the reply."""
    del said, sent
    c, t = m.c, m.t
    last = next((u for u in reversed(t.prior) if u.speaker is Speaker.COMPANION), None)
    if last is None:
        return
    keys = (*MENTION_KEYS, ASKED_HOW_THEY_ARE)
    offered = next(
        (
            d
            for d in c.store.decisions_for_turn(c.rel, last.turn_id)
            if any(d.has_key(k) for k in keys)
        ),
        None,
    )
    if offered is None or c.store.decided_since(c.rel, MET, offered.at):
        return
    found = offered.detail or {}
    about = str(found.get("about") or found.get("claim") or "how they are after a heavy talk")
    got = await ask(m.judge, MET_JUDGE, met_prompt(about, last.text, t.text))
    met = got.value.value if got is not None else None
    detail: dict[str, Json] = {
        "about": about,
        "loop_id": found.get("loop_id"),
        "met": met,
        "prompt": MET_PROMPT.ref,
    }
    decide(c, t, MET, detail, reason=f"{MET}: {met or 'not read'}, about {about}")
