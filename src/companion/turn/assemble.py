"""The assemble stage of a turn: the card, the clock and every note, built into the request."""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from companion.core.card import (
    EVENT_SHOWN_DAYS,
    Card,
    Focus,
    build_card,
    day_over,
    everyday_ids,
    render,
)
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
    Frame,
    Speaker,
    Utterance,
)
from companion.core.views import card_views, why
from companion.kit.current import Turn, decide, mark, recorder
from companion.kit.features import CardLane, Lookups, Moment
from companion.kit.record import Recorder
from companion.registry import FEATURES
from companion.turn.notes import Notes, notes_for
from companion.turn.values import Routed, moment_of

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime

log = logging.getLogger("companion.turn")


@dataclass(frozen=True, slots=True)
class CardLog:
    """Records where each belief went this turn: into the card, or held back."""

    record: Recorder
    view_reasons: dict[BeliefId, str]

    def write(self, card: Card) -> None:
        for b in card.usable:
            self._one(DecisionKind.SURFACE, b, "in the card")
        for b in card.guarded:
            self._one(
                DecisionKind.WITHHOLD, b, f"sensitivity {b.sensitivity}: known, held for listening"
            )
        for b in card.older:
            self._one(DecisionKind.SURFACE, b, "in the card as older, possibly out of date")
        if card.kept_back:
            self.record.decide(
                "card: held left out",
                {"kept_back": [b.id for b in card.kept_back]},
                reason=f"card: {len(card.kept_back)} guarded memories left out, the turn is casual",
            )
        if card.crowded:
            self.record.decide(
                "card: crowded out",
                {"crowded": [b.id for b in card.crowded]},
                reason=f"card: {len(card.crowded)} current beliefs crowded out, it holds "
                f"{len(card.usable) + len(card.guarded)}",
            )
        for b in card.dropped:
            self._one(DecisionKind.WITHHOLD, b, self._why_dropped(b, card))
        for b in card.views:
            self._one(DecisionKind.SURFACE, b, self.view_reasons[b.id])

    @staticmethod
    def _why_dropped(b: Belief, card: Card) -> str:
        last = when_phrase(card.aged[b.id].last_supported, card.now)
        if day_over(b, card.now):
            return f"bound to a day that is over (last mentioned {last}); still in memory"
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
        f" card {len(card_text)} chars ({len(card.usable)} usable, {len(card.guarded)} guarded,"
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
    now: datetime | None = None  # when their message came, for a pause before it in the history

    def request(self) -> TalkerRequest:
        """The system block in tags, the history and their message, then the scene reminder and
        the notes' tail after the history, where it weighs most."""
        pinned = [self.pinned] if self.pinned else []
        card = tagged("\n".join([self.clock, *pinned, *self.memory, *self.notes.lines]))
        request = build_request(self.prefix, to_messages(self.prior, self.now), self.text, "", card)
        tail = "\n".join([*([self.scene] if self.scene else []), *self.notes.tail])
        return dataclasses.replace(request, tail=tail) if tail else request


@dataclass(frozen=True, slots=True)
class Assembled:
    """What one turn sends and what it needs to record afterwards."""

    request: TalkerRequest
    card_text: str
    card: Card
    cards: CardLog  # where each belief went, written once the turn is stored
    moment: Moment  # the turn as the hooks after the request read it
    after: Sequence[Callable[[], None]] = ()  # the notes' writes, made once the turn is stored


def _lane(c: Runtime, t: Turn, looked: Lookups, *, roleplay: bool, card: Card) -> CardLane:
    """What the features' lanes do to the card, joined: the first card sent instead wins, memories
    left off and pinned text and writes add up."""
    lanes = [
        f.lane(c, t, looked, roleplay=roleplay, card=card)
        for f in FEATURES
        if f.lane is not None and f.live(c)
    ]
    text = next((lane.text for lane in lanes if lane.text is not None), None)
    return CardLane(
        frozenset[BeliefId]().union(*(lane.hidden for lane in lanes)),
        text,
        "\n".join(lane.pinned for lane in lanes if lane.pinned),
        tuple(w for lane in lanes for w in lane.after),
    )


def assemble(c: Runtime, t: Turn, routed: Routed, looked: Lookups) -> Assembled:
    """The request for this turn: the card, the clock and every note (`turn/notes.py`)."""
    store, now = c.store, t.now
    in_scene = routed.in_scene
    roleplay = routed.talker is c.roleplay_talker
    crisis = routed.crisis
    moment = dataclasses.replace(
        moment_of(c, t, routed),
        looked=looked,
        risk=crisis is not None and crisis.acts and crisis.risk,
    )
    view_state = store.view_state(c.rel)
    views = card_views(store.self_beliefs(c.rel), view_state)
    assertable = [b for b in store.user_beliefs(c.rel) if is_assertable(b)]
    labels = store.belief_labels(c.rel)
    support, contexts = store.last_support(c.rel), store.belief_contexts(c.rel)
    focus = looked.find(Focus)

    def card_of(beliefs: Sequence[Belief], shown_views: Sequence[Belief]) -> Card:
        return build_card(
            beliefs,
            support,
            now,
            views=shown_views,
            show_guarded=moment.sharing,
            everyday=everyday_ids(labels),
            contexts=contexts,
            focus=focus,
        )

    card = card_of(assertable, views)
    if focus is not None:
        shown_ids = [b.id for b in (*card.usable, *card.guarded)]
        decide(
            c,
            t,
            "card: by focus",
            {"closeness": {b: round(focus.closeness.get(b, 0.0), 3) for b in shown_ids}},
            reason=f"card: {len(shown_ids)} memories, after the rules the closest to the moment",
        )
    lane = _lane(c, t, looked, roleplay=roleplay, card=card)
    if lane.text is not None:  # a scene turn: the scene card, and no everyday memories
        card, shown = card_of([], ()), [lane.text] if lane.text else []
    else:
        if lane.hidden & {b.id for b in assertable}:
            assertable = [b for b in assertable if b.id not in lane.hidden]
            card = card_of(assertable, views)
        shown = [] if card.empty else [render(card)]
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    clock = now_line(now, theirs[-1].at if theirs else None)
    pinned = address_note(store.setting(c.rel, ADDRESS_KEY))
    on_card = frozenset(b.id for b in (*card.usable, *card.guarded, *card.older))
    moment = dataclasses.replace(moment, beliefs=assertable, on_card=on_card)
    notes = notes_for(moment)
    prefix = c.roleplay_prefix if roleplay and c.roleplay_prefix is not None else c.prefix
    scene = "\n".join(p for p in (c.scene_reminder if roleplay else "", lane.pinned) if p)
    request = Layout(prefix, t.prior, t.text, clock, pinned, shown, notes, scene, now).request()
    if request.tail:
        decide(c, t, TAIL, {"text": request.tail})  # what replay needs to rebuild it
    store.save_prefix(prefix)
    _mark_start(t, in_scene, card, request.card)
    cards = CardLog(recorder(c, t), {b.id: why(b, view_state) for b in views})
    return Assembled(request, request.card, card, cards, moment, (*notes.after, *lane.after))
