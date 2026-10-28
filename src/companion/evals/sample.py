"""One eval sample as the person would receive it, made by the turn's own code (owner's decision,
2026-10-24).

A scripted fixture is laid out as its turn would be: its history is stored in a throwaway
conversation, the turn's notes are chosen for that moment (`turn/notes.py`) and the request is laid
out by `Layout` (`turn/assemble.py`). The fixture gives the readings a judge would (`labels`,
`lore`); every other judge fails and every other look-up finds nothing, which the turn reads as no
note. A recorded turn replays the request it logged. Either way the reply then passes the turn's
reply checks and their redraws (`turn/talk.py`), with the quip judge asked for real, unless the
variant is raw.
"""

from __future__ import annotations

import tempfile
import uuid
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.extractor import Extraction, StructuredModel
from companion.core.history import HISTORY_LIMIT
from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import Message, TalkerRequest
from companion.core.talker import Reply, Talker
from companion.core.turn.listening import ListeningRead
from companion.core.types import (
    Frame,
    Json,
    RelationshipId,
    SessionId,
    Speaker,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.evals.fixtures import Fixture, Script
from companion.evals.rebuild import swap_memory
from companion.features.basics.logic import ASKED as ASKED_NAME
from companion.features.lore.run import LORE
from companion.loops.current import Heard, Turn
from companion.loops.features import Lookups, Moment
from companion.loops.record import Recorder
from companion.loops.runtime import Runtime
from companion.store.sqlite.store import Store
from companion.turn.assemble import Layout
from companion.turn.notes import Notes, notes_for
from companion.turn.talk import checked

REL = RelationshipId("eval")
SESSION = SessionId("eval")
CLOCK = "Right now it is Thursday 12:00."  # a script with no clock line of its own
READ_BY = "fixture"  # the scorer named on a reading the fixture gives
EMPTY = "the model returned no text"


@dataclass(frozen=True, slots=True)
class Variant:
    label: str
    prefix: Prefix
    keep_card: bool = True
    model: str | None = None
    history: int | None = None  # keep only this many of the last messages
    effort: str | None = None  # reasoning effort; None keeps it off, as in the bot
    roleplay: bool = False  # answered as a pretend scene, as the roleplay talker answers one
    scene: str = ""  # the character's scene reminder, sent after the history with roleplay
    raw: bool = False  # the model's first reply, without the turn's checks and redraws
    card_notes: tuple[str, ...] = ()  # a note's text added to the system block's notes
    tail_notes: tuple[str, ...] = ()  # a note's text sent after the history


@dataclass(frozen=True, slots=True)
class Drawn:
    """What was sent, the reply the person would receive, and what made the turn draw again."""

    request: TalkerRequest
    reply: Reply
    redrawn: tuple[str, ...]


class Unread:
    """Every judge but the reply checks' own: a call that fails, which the turn reads as nothing
    found."""

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        msg = "an eval sample asks no judge but the reply checks' own"
        raise RuntimeError(msg)


def noted(card: str, lines: Sequence[str]) -> str:
    """A recorded system block with notes added at the end of its notes: inside the `<notes>` tag
    when it has one, else as bracketed lines after the rest."""
    if not lines:
        return card
    end = card.rfind("\n</notes>")
    if end < 0:
        return "\n".join([card, *(_bracketed(x) for x in lines)])
    added = "".join(f"\n{_bracketed(x)[1:-1]}" for x in lines)
    return card[:end] + added + card[end:]


def _bracketed(text: str) -> str:
    """A note's line as the notes are written, so the tags gather it with the others."""
    return text if text.startswith("[") and text.endswith("]") else f"[{text}]"


def recorded_request(base: TalkerRequest, v: Variant) -> TalkerRequest:
    """A recorded turn's request as it was logged, with the variant's prefix, history, card and
    notes. A scene reminder it did not send is put first after the history, as a scene turn has it.
    Without the card, a message from before the card moved to the system block loses its memory
    blocks too; its clock line and what they typed stay."""
    messages = list(base.messages)
    if v.history is not None:
        messages = messages[-v.history :]
    card = base.card
    if not v.keep_card:
        messages[-1] = Message(messages[-1].role, swap_memory(messages[-1].content, ""))
        card = swap_memory(card, "").strip()
    scene = [v.scene] if v.roleplay and v.scene and v.scene not in base.tail else []
    tail = "\n".join([*scene, *([base.tail] if base.tail else []), *v.tail_notes])
    return TalkerRequest(v.prefix, tuple(messages), noted(card, v.card_notes), tail)


def _script_turn(c: Runtime, script: Script, v: Variant) -> Turn:
    """Their message as a turn over the script's history, stored as their messages and its replies
    a minute apart and read back as the turn reads it. It already asked what to call them today,
    so that note stays out, as it would in an established relationship."""
    now = utc_now()
    n = len(script.history)
    for i, (role, text) in enumerate(script.history):
        c.store.append_utterance(
            Utterance(
                UtteranceId(uuid.uuid4().hex),
                REL,
                SESSION,
                TurnId(uuid.uuid4().hex),
                Speaker.USER if role == "user" else Speaker.COMPANION,
                text,
                Frame.REAL,
                "eval",
                now - timedelta(minutes=n + 1 - i),
            )
        )
    prior = c.store.history_before(REL, now, HISTORY_LIMIT)
    if v.history is not None:
        prior = prior[max(0, len(prior) - v.history + 1) :]
    t = Turn(SESSION, TurnId(uuid.uuid4().hex), now, prior, script.user)
    Recorder(c.store, REL, SESSION, t.turn, TraceId(t.turn), now).decide(
        ASKED_NAME, at=now - timedelta(hours=1)
    )
    return t


def reading(
    v: Variant, labels: tuple[int, str, bool, bool, bool] | None
) -> tuple[Frame, Heard | None]:
    """The frame the turn is answered in, and the listening judge's reading as the fixture gives
    it. A roleplay variant answers a pretend scene, where the listening judge is not asked."""
    if v.roleplay:
        return Frame.PLAY, None
    if labels is None:
        return Frame.REAL, None
    severity, stance, vague, medical, rude = labels
    return Frame.REAL, (ListeningRead(severity, stance, vague, medical, rude), READ_BY, "")


def script_request(c: Runtime, t: Turn, script: Script, v: Variant) -> TalkerRequest:
    """The request the turn would send for this script: its notes for the moment, the fixture's
    memory block and clock line, then the variant's notes."""
    in_scene, heard = reading(v, script.labels)
    looked = Lookups(found={LORE.name: script.lore} if script.lore else {})
    notes = notes_for(Moment(c, t, in_scene, heard, looked, held=False, beliefs=()))
    memory = [script.memory] if v.keep_card and script.memory else []
    return Layout(
        c.prefix,
        t.prior,
        t.text,
        script.clock or CLOCK,
        None,
        memory,
        Notes((*notes.lines, *map(_bracketed, v.card_notes)), (), (*notes.tail, *v.tail_notes)),
        v.scene if v.roleplay else "",
        t.now,
    ).request()


@contextmanager
def _scratch(talker: Talker, prefix: Prefix, *, roleplay: bool) -> Generator[Runtime]:
    """A conversation over an empty store in a temporary directory, with the switches the live bot
    defaults to; gone after the sample."""
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "eval.sqlite")
        try:
            yield Runtime(
                store,
                talker,
                prefix,
                REL,
                judge=Unread(),
                roleplay_talker=talker if roleplay else None,
                resample=True,
                marks=True,
                mood="shadow",
            )
        finally:
            store.close()


def _redraws(store: Store, turn: TurnId) -> tuple[str, ...]:
    """What made the turn draw again, from the checks' logged decisions."""
    out: list[str] = []
    for d in store.decisions_for_turn(REL, turn):
        checks = d.detail.get("checks") if isinstance(d.detail, dict) else None
        if d.has_key("resampled"):
            out.append(EMPTY)
        elif d.has_key("recheck") and isinstance(checks, list):
            out.extend(str(x) for x in checks)
    return tuple(out)


async def draw(
    f: Fixture, v: Variant, recorded: TalkerRequest | None, talker: Talker, judge: StructuredModel
) -> Drawn:
    """One sample: the request, the model's reply, and unless the variant is raw, that reply after
    the turn's checks with the reply checks' own judge."""
    in_scene, heard = reading(v, f.script.labels if f.script is not None else f.labels)
    with _scratch(talker, v.prefix, roleplay=v.roleplay) as c:
        if f.script is not None:
            t = _script_turn(c, f.script, v)
            request = script_request(c, t, f.script, v)
        else:
            assert recorded is not None
            request = recorded_request(recorded, v)
            text = request.messages[-1].content
            t = Turn(SESSION, TurnId(uuid.uuid4().hex), utc_now(), [], text)
        first = await talker.reply(request)
        if v.raw:
            return Drawn(request, first, ())
        checking = replace(c, judge=judge)
        reply = await checked(checking, t, request, first, heard, in_scene, talker, held=False)
        return Drawn(request, reply, _redraws(c.store, t.turn))
