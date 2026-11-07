"""A record of one memory pass."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from companion.core.types import RelationshipId, UtteranceId

BATCH = 40  # messages a pass reads per call, and every reader that goes by the pass's batches
CONTEXT = 4  # messages before a batch shown with it, for context


@dataclass(frozen=True, slots=True)
class PassRun:
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
