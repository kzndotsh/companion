"""Rebuild a recorded turn with a different card size or a longer history, from the database as it
stood at that turn (`+cardN`, `+histN`). The persona and the notes stay as recorded; only the memory
blocks or the messages change, so a difference is the change under test."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from companion.core.card import build_card, render
from companion.core.frames import is_assertable
from companion.core.history import to_messages
from companion.core.prompt.request import TalkerRequest
from companion.features.knowing.logic import Depth, Domain
from companion.store.sqlite.replay import replay_file
from companion.store.sqlite.store import Store

ALL = 10_000
_MEMORY = re.compile(
    r"^\[(?:What you remember|Also known|Older, and may be out of date).*?\]\n?",
    re.MULTILINE | re.DOTALL,
)


def swap_memory(card: str, memory: str) -> str:
    """The card with its memory blocks replaced, at the place the first one stood."""
    found = _MEMORY.search(card)
    if found is None:
        lines = card.split("\n", 1)
        return "\n".join([lines[0], memory, *lines[1:]]) if memory else card
    rest = _MEMORY.sub("", card)
    head, tail = rest[: found.start()], rest[found.start() :]
    return head + (memory + "\n" if memory else "") + tail


def rebuilt(
    db: Path, turn_id: str, *, card_size: int | None = None, history: int | None = None
) -> TalkerRequest:
    report = replay_file(db, turn_id)
    base, record = report.request, report.record
    at, rel = record.at, record.relationship_id
    store = Store(db)
    try:
        request = base
        if card_size is not None:
            beliefs = [b for b in store.user_beliefs_as_of(rel, at) if is_assertable(b)]
            support = {bid: min(when, at) for bid, when in store.last_support(rel).items()}
            labels = store.belief_labels(rel)
            everyday = {
                bid
                for bid, x in labels.items()
                if x.domain is Domain.DAILY and x.depth is Depth.SURFACE
            }
            card = build_card(
                beliefs,
                support,
                at,
                max_items=card_size,
                show_held="[Also known" in base.card,
                everyday=everyday,
            )
            request = replace(request, card=swap_memory(base.card, render(card)))
        if history is not None:
            said = base.messages[-1]
            prior = [u for u in store.history_before(rel, at, history + 1) if u.turn_id != turn_id]
            request = replace(request, messages=(*to_messages(prior[-history:]), said))
    finally:
        store.close()
    return request
