"""A record of one slow-loop pass."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from companion.core.types import RelationshipId, UtteranceId


@dataclass(frozen=True, slots=True)
class ReflectRun:
    id: str
    relationship_id: RelationshipId
    upto_at: datetime
    upto_id: UtteranceId
    n_utterances: int
    n_candidates: int
    n_accepted: int
    n_rejected: int
    model: str
    cost_usd: float
    latency_ms: int
    at: datetime
