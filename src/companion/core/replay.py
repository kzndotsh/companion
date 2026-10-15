"""Rebuild exactly what the fast loop saw for one turn.

The ledger is append-only, so the history before a turn can never change after the fact. A turn
record stores the prefix hash, the volatile context and the request hash; everything else is
derived, and the rebuilt request must hash to the recorded one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import (
    Message,
    TalkerRequest,
    build_request,
    request_sha256,
)
from companion.core.types import RelationshipId, SessionId, Speaker, TurnId, Utterance


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


class ReplayError(ValueError):
    """The turn cannot be rebuilt from the ledger."""


def _role(u: Utterance) -> str:
    return "user" if u.speaker is Speaker.USER else "assistant"


def rebuild_request(
    record: TurnRecord, prefix: Prefix, session_utterances: Sequence[Utterance]
) -> TalkerRequest:
    """`session_utterances` is the whole session, in ledger order. Later turns are ignored."""
    ordered = sorted(session_utterances, key=lambda u: (u.at, u.id))
    current = [u for u in ordered if u.turn_id == record.turn_id and u.speaker is Speaker.USER]
    if len(current) != 1:
        msg = f"turn {record.turn_id} needs exactly one user utterance, found {len(current)}"
        raise ReplayError(msg)
    user = current[0]
    if prefix.sha256 != record.prefix_sha256:
        msg = "prefix does not match the one recorded for this turn"
        raise ReplayError(msg)
    before = ordered[: ordered.index(user)]
    history = [Message(_role(u), u.text) for u in before]  # pyright: ignore[reportArgumentType]
    return build_request(prefix, history, user.text, record.volatile)


def matches_record(record: TurnRecord, rebuilt: TalkerRequest) -> bool:
    return request_sha256(rebuilt) == record.request_sha256
