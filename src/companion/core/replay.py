"""Rebuild exactly what the fast loop saw for one turn.

The ledger is append-only, so the history before a turn never changes after the fact. A turn
record stores the prefix hash, the volatile context, the memory card and the request hash;
everything else is derived, and the rebuilt request must hash to the recorded one.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from companion.core.history import to_messages
from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import TalkerRequest, build_request, request_sha256
from companion.core.types import RelationshipId, SessionId, TurnId, Utterance


@dataclass(frozen=True, slots=True)
class TurnRecord:
    turn_id: TurnId
    relationship_id: RelationshipId
    session_id: SessionId
    prefix_sha256: str
    volatile: str
    request_sha256: str
    model: str | None
    at: datetime
    card: str = ""


class ReplayError(ValueError):
    """The turn cannot be rebuilt from the ledger."""


TAIL = "tail: sent after the history"


def rebuild_request(
    record: TurnRecord,
    prefix: Prefix,
    user: Utterance,
    history: Sequence[Utterance],
    tail: str = "",
) -> TalkerRequest:
    """`history` is the windowed past before `user`, exactly as the live loop fetched it; `tail` is
    what the turn logged under TAIL, sent after it."""
    if user.turn_id != record.turn_id:
        msg = f"utterance {user.id} belongs to turn {user.turn_id}, not {record.turn_id}"
        raise ReplayError(msg)
    if prefix.sha256 != record.prefix_sha256:
        msg = "prefix does not match the one recorded for this turn"
        raise ReplayError(msg)
    request = build_request(prefix, to_messages(history), user.text, record.volatile, record.card)
    return dataclasses.replace(request, tail=tail) if tail else request


def matches_record(record: TurnRecord, rebuilt: TalkerRequest) -> bool:
    return request_sha256(rebuilt) == record.request_sha256
