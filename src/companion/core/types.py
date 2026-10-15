"""The shapes the whole system speaks. Illegal combinations raise at construction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import NewType

RelationshipId = NewType("RelationshipId", str)
SessionId = NewType("SessionId", str)
TurnId = NewType("TurnId", str)
UtteranceId = NewType("UtteranceId", str)
BeliefId = NewType("BeliefId", str)


class Speaker(StrEnum):
    USER = "user"
    COMPANION = "companion"


class Frame(StrEnum):
    REAL = "real"
    PLAY = "play"
    STORY = "story"
    HYPOTHETICAL = "hypothetical"
    OOC = "ooc"


class Provenance(StrEnum):
    STATED = "stated"
    INFERRED = "inferred"
    JOKED = "joked"
    PLAYED = "played"
    HYPOTHETICAL = "hypothetical"
    THIRD_PARTY = "third_party"
    COMPANION_SAID = "companion_said"


class Subject(StrEnum):
    USER = "user"
    SELF = "self"
    RELATIONSHIP = "relationship"
    WORLD = "world"


class BeliefKind(StrEnum):
    TRAIT = "trait"
    STATE = "state"
    EVENT = "event"
    PREFERENCE = "preference"
    THREAD = "thread"
    BOUNDARY = "boundary"
    TELL = "tell"
    PROMISE = "promise"


NON_REAL_FRAMES = frozenset({Frame.PLAY, Frame.STORY, Frame.HYPOTHETICAL})
SINCERE_PROVENANCE = frozenset({Provenance.STATED, Provenance.INFERRED})


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = f"{name} must be timezone-aware"
        raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Utterance:
    id: UtteranceId
    relationship_id: RelationshipId
    session_id: SessionId
    turn_id: TurnId
    speaker: Speaker
    text: str
    frame: Frame
    channel: str
    at: datetime

    def __post_init__(self) -> None:
        if not self.text:
            msg = "utterance text must not be empty"
            raise ValueError(msg)
        _require_aware("at", self.at)


@dataclass(frozen=True, slots=True)
class Evidence:
    """A verbatim quote from one utterance. Only `verify.evidence_from` should build these."""

    utterance_id: UtteranceId
    quote: str

    def __post_init__(self) -> None:
        if not self.quote.strip():
            msg = "evidence quote must not be empty"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Belief:
    id: BeliefId
    relationship_id: RelationshipId
    subject: Subject
    kind: BeliefKind
    claim: str
    evidence: tuple[Evidence, ...]
    provenance: Provenance
    speaker: Speaker
    frame: Frame
    confidence: float
    valid_from: datetime
    recorded_at: datetime
    sensitivity: int = 0
    valid_until: datetime | None = None
    superseded_by: BeliefId | None = None

    def __post_init__(self) -> None:
        if not self.claim.strip():
            msg = "belief claim must not be empty"
            raise ValueError(msg)
        if not self.evidence:
            msg = "a belief needs at least one verified quote"
            raise ValueError(msg)
        if not 0.0 <= self.confidence <= 1.0:
            msg = "confidence must be within [0, 1]"
            raise ValueError(msg)
        if not 0 <= self.sensitivity <= 3:
            msg = "sensitivity must be within [0, 3]"
            raise ValueError(msg)
        _require_aware("valid_from", self.valid_from)
        _require_aware("recorded_at", self.recorded_at)
        if self.valid_until is not None:
            _require_aware("valid_until", self.valid_until)
            if self.valid_until < self.valid_from:
                msg = "valid_until precedes valid_from"
                raise ValueError(msg)
        if self.superseded_by is not None and self.valid_until is None:
            msg = "a superseded belief must be closed with valid_until"
            raise ValueError(msg)
        # The companion's own words can never become a fact about the user, and the
        # user's words can never be tagged as the companion's. Provenance follows speaker.
        if (self.speaker is Speaker.COMPANION) != (self.provenance is Provenance.COMPANION_SAID):
            msg = "provenance companion_said holds exactly when the speaker is the companion"
            raise ValueError(msg)
        # Play, story and hypotheticals cannot be recorded as sincere statements.
        if self.frame in NON_REAL_FRAMES and self.provenance in SINCERE_PROVENANCE:
            msg = f"frame {self.frame} cannot carry sincere provenance {self.provenance}"
            raise ValueError(msg)

    @property
    def is_current(self) -> bool:
        return self.valid_until is None
