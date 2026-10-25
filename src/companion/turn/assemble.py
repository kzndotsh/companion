"""The assemble stage of a turn: the card, the clock and every note, built into the request."""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC
from typing import TYPE_CHECKING

from companion.core.card import EVENT_SHOWN_DAYS, Card, build_card, render
from companion.core.clock import now_line
from companion.core.frames import (
    is_assertable,
)
from companion.core.freshness import HORIZON_DAYS, when_phrase
from companion.core.history import to_messages
from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import TalkerRequest, build_request
from companion.core.prompt.sections import tagged
from companion.core.replay import TAIL
from companion.core.turn.address import KEY as ADDRESS_KEY
from companion.core.turn.address import address_note
from companion.core.types import (
    Belief,
    BeliefId,
    DecisionKind,
    Depth,
    Domain,
    Frame,
    Speaker,
    Utterance,
)
from companion.core.views import ViewState, card_views
from companion.loops.current import Heard, Turn, decide, mark
from companion.loops.features import Lookups, Moment
from companion.loops.record import Recorder
from companion.turn.notes import Notes, notes_for

if TYPE_CHECKING:
    from companion.loops.conversation import Conversation

log = logging.getLogger("companion.turn")


@dataclass(frozen=True, slots=True)
class CardLog:
    """Records where each belief went this turn: into the card, or held back."""

    record: Recorder
    view_reasons: dict[BeliefId, str]

    def write(self, card: Card) -> None:
        for b in card.usable:
            self._one(DecisionKind.SURFACE, b, "in the card")
        for b in card.held:
            self._one(
                DecisionKind.WITHHOLD, b, f"sensitivity {b.sensitivity}: known, held for listening"
            )
        for b in card.older:
            self._one(DecisionKind.SURFACE, b, "in the card as older, possibly out of date")
        if card.kept_back:
            self.record.decide(
                "card: held left out",
                {"kept_back": [b.id for b in card.kept_back]},
                reason=f"card: {len(card.kept_back)} held beliefs left out, the turn is casual",
            )
        if card.crowded:
            self.record.decide(
                "card: crowded out",
                {"crowded": [b.id for b in card.crowded]},
                reason=f"card: {len(card.crowded)} current beliefs crowded out, it holds "
                f"{len(card.usable) + len(card.held)}",
            )
        for b in card.dropped:
            self._one(DecisionKind.WITHHOLD, b, self._why_dropped(b, card))
        for b in card.views:
            self._one(DecisionKind.SURFACE, b, self.view_reasons[b.id])

    @staticmethod
    def _why_dropped(b: Belief, card: Card) -> str:
        last = when_phrase(card.aged[b.id].last_supported, card.now)
        horizon = HORIZON_DAYS[b.kind]
        if horizon is None:  # an event: history, only left out once it is an old one-day moment
            return (
                f"a one-day moment of daily life last mentioned {last}, not shown after"
                f" {EVENT_SHOWN_DAYS} days; still in memory"
            )
        return f"stale: last mentioned {last}, past its {horizon}-day horizon, so left out"

    def _one(self, kind: DecisionKind, belief: Belief, reason: str) -> None:
        key = "card: surfaced" if kind is DecisionKind.SURFACE else "card: withheld"
        self.record.decide(key, reason=reason, kind=kind, belief=belief.id)


def _mark_start(t: Turn, in_scene: Frame, card: Card, card_text: str) -> None:
    mark(
        t,
        f"start: {len(t.prior)} history messages, scene={in_scene.value},"
        f" card {len(card_text)} chars ({len(card.usable)} usable, {len(card.held)} held,"
        f" {len(card.older)} older, {len(card.dropped)} dropped, {len(card.views)} views),"
        f" text {len(t.text)} chars",
    )


@dataclass(frozen=True, slots=True)
class Layout:
    """A turn's request from its parts, with no store in reach: the eval runner lays out a scripted
    fixture with this too, so a sample is shaped as the person's turn would be."""

    prefix: Prefix
    prior: Sequence[Utterance]
    text: str
    clock: str
    pinned: str | None
    memory: Sequence[str]  # the rendered memory block, or nothing
    notes: Notes
    scene: str = ""  # the character's scene reminder, on a roleplay turn

    def request(self) -> TalkerRequest:
        """The system block in tags, the history and their message, then the scene reminder and
        the notes' tail after the history, where it weighs most."""
        pinned = [self.pinned] if self.pinned else []
        card = tagged(
            "\n".join([self.clock, *pinned, *self.memory, *self.notes.lines]), memory=False
        )
        request = build_request(self.prefix, to_messages(self.prior), self.text, "", card)
        tail = "\n".join([*([self.scene] if self.scene else []), *self.notes.tail])
        return dataclasses.replace(request, tail=tail) if tail else request


@dataclass(frozen=True, slots=True)
class Assembled:
    """What one turn sends and what it needs to record afterwards."""

    request: TalkerRequest
    card_text: str
    card: Card
    views: Sequence[Belief]
    view_state: ViewState
    after: Sequence[Callable[[], None]] = ()  # the notes' writes, made once the turn is stored


def assemble(  # noqa: PLR0913
    c: Conversation,
    t: Turn,
    in_scene: Frame,
    heard: Heard | None,
    looked: Lookups,
    *,
    held: bool = False,
    brushed: bool = False,
    roleplay: bool = False,
) -> Assembled:
    """The request for this turn: the card, the clock and every note (`turn/notes.py`)."""
    store, now = c.store, t.now
    view_state = store.view_state(c.rel)
    views = card_views(store.self_beliefs(c.rel), view_state)
    assertable = [b for b in store.user_beliefs(c.rel) if is_assertable(b)]
    sharing = heard is not None and heard[0].severity >= 1
    labels = store.belief_labels(c.rel)
    everyday = {
        bid for bid, x in labels.items() if x.domain is Domain.DAILY and x.depth is Depth.SURFACE
    }
    card = build_card(
        assertable,
        store.last_support(c.rel),
        now,
        views=views,
        show_held=sharing,
        everyday=everyday,
        contexts=store.belief_contexts(c.rel),
    )
    shown = [] if card.empty else [render(card, now.astimezone().tzinfo or UTC)]
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    clock = now_line(now, theirs[-1].at if theirs else None)
    pinned = address_note(store.setting(c.rel, ADDRESS_KEY))
    on_card = frozenset(b.id for b in (*card.usable, *card.held, *card.older))
    notes = notes_for(Moment(c, t, in_scene, heard, looked, held, assertable, on_card, brushed))
    prefix = c.roleplay_prefix if roleplay and c.roleplay_prefix is not None else c.prefix
    scene = c.scene_reminder if roleplay else ""
    request = Layout(prefix, t.prior, t.text, clock, pinned, shown, notes, scene).request()
    if request.tail:
        decide(c, t, TAIL, {"text": request.tail})  # what replay needs to rebuild it
    store.save_prefix(prefix)
    _mark_start(t, in_scene, card, request.card)
    return Assembled(request, request.card, card, views, view_state, notes.after)
