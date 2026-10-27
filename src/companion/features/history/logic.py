"""Its own history (ADR 0025): small details of its own past it makes up in chat, kept as canon.

A small model picks the details out of its own messages (`system/history-capture`). Code keeps one
only when its quote is in one of its own messages, never from a what-if, and from a pretend scene
only when it was said in passing as true of itself, not as something that happens in the scene.
A second model reads each new story against the character sheet and the stories already canon
(`system/history-canon`), three times; code turns the reads into its standing. Step 1 is shadow:
nothing reaches the talker.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import NewType

from companion.core.beliefs.verify import QuoteNotFoundError, evidence_from
from companion.core.types import Frame, Json, RelationshipId, Speaker, Utterance, UtteranceId
from companion.core.vectors import Vector, dot
from companion.prompts import get

CAPTURE = get("system/history-capture")
CANON = get("system/history-canon")
SHOWN = 2  # at most this many stories it would show a turn
GATE = 0.3  # a story less like their message than this is not shown

StoryId = NewType("StoryId", str)


class Place(StrEnum):
    ITS_PAST = "its_past"  # true of itself, outside any scene
    SCENE = "scene"  # happens inside a pretend scene or story


class Verdict(StrEnum):
    FITS = "fits"
    SAME = "same"
    CONTRADICTS = "contradicts"
    TOO_BIG = "too_big"
    NOT_A_STORY = "not_a_story"


class Standing(StrEnum):
    CANON = "canon"
    EVIDENCE = "evidence"  # the same story as an earlier one, kept as a telling of it
    NOT_CANON = "not_canon"
    RETIRED = "retired"  # the owner retired it


# A what-if is never its past. In a pretend scene or story only what the reader placed in its own
# past counts, not what happens in the scene (owner's decision 2); outside one that label is
# expected anyway, and a scene label there is dropped too.
_NEVER = frozenset({Frame.HYPOTHETICAL})

CAPTURE_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "stories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "quote": {"type": "string"},
                    "claim": {"type": "string"},
                    "place": {"type": "string", "enum": [p.value for p in Place]},
                },
                "required": ["message", "quote", "claim", "place"],
            },
        }
    },
    "required": ["stories"],
}

CANON_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": [v.value for v in Verdict]},
        "story": {"type": "string"},
    },
    "required": ["verdict", "story"],
}


@dataclass(frozen=True, slots=True)
class Proposed:
    message: str
    quote: str
    claim: str
    place: str


@dataclass(frozen=True, slots=True)
class Story:
    """A detail of its own past, in the words it said, with the message's frame (ADR 0001, 0010)."""

    id: StoryId
    relationship_id: RelationshipId
    utterance_id: UtteranceId
    quote: str
    claim: str
    frame: Frame
    at: datetime  # when it was said


@dataclass(frozen=True, slots=True)
class CanonRead:
    verdict: Verdict
    of: StoryId | None  # the kept story it is the same as or contradicts


@dataclass(frozen=True, slots=True)
class Ruling:
    standing: Standing
    verdict: Verdict | None  # None for the owner's retire
    of: StoryId | None
    reason: str  # written by code


@dataclass(frozen=True, slots=True)
class Recorded:
    """A story with its newest event (None while it waits for the canon check), and the stories
    kept as evidence of it."""

    story: Story
    standing: Standing | None
    of: StoryId | None
    reason: str
    evidence: tuple[Story, ...] = ()

    @property
    def told(self) -> tuple[UtteranceId, ...]:
        """Its own messages it was told in: the first telling and each one kept as evidence."""
        return (self.story.utterance_id, *(e.utterance_id for e in self.evidence))

    @property
    def last_told(self) -> datetime:
        return max(s.at for s in (self.story, *self.evidence))


def nearest(
    query: Vector, canon: Sequence[Recorded], vectors: Mapping[StoryId, Vector]
) -> list[tuple[Recorded, float]]:
    """The canon stories closest to the query, at most SHOWN and none below GATE, closest first. A
    story with no vector yet is left out."""
    scored = [(r, dot(query, vectors[r.story.id])) for r in canon if r.story.id in vectors]
    return [x for x in sorted(scored, key=lambda x: -x[1])[:SHOWN] if x[1] >= GATE]


def parse_capture(data: Json) -> list[Proposed] | None:
    """The proposed stories, or None when the answer does not have the shape asked for."""
    items = data.get("stories") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    out: list[Proposed] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        fields = [item.get(k) for k in ("message", "quote", "claim", "place")]
        if all(isinstance(v, str) for v in fields):
            out.append(Proposed(*(str(v).strip() for v in fields)))
    return out


def to_story(p: Proposed, window: Mapping[str, Utterance], story_id: str) -> Story | str:
    """A story code keeps, or the reason it was dropped."""
    u = window.get(p.message.strip("[] "))
    if u is None or u.speaker is not Speaker.COMPANION:
        return "not one of its own messages"
    if not p.claim:
        return "no claim"
    try:
        quote = evidence_from(u, p.quote).quote
    except QuoteNotFoundError:
        return "quote not in the message"
    if u.frame in _NEVER:
        return "said in a what-if"
    if p.place != Place.ITS_PAST:
        return "something that happens in the scene, not its own past"
    return Story(StoryId(story_id), u.relationship_id, u.id, quote, p.claim, u.frame, u.at)


def canon_prompt(sheet: str, canon: Sequence[Story], new: Story) -> tuple[str, dict[str, StoryId]]:
    """The sheet, the kept stories under short labels, and the new story; with the labels back."""
    refs = {f"s{n}": s.id for n, s in enumerate(canon, 1)}
    kept = [f'[{ref}] {s.claim} (it said: "{s.quote}")' for ref, s in zip(refs, canon, strict=True)]
    text = [
        "Character sheet:",
        sheet.strip() or "(none: it has no authored past)",
        "",
        "Stories kept as canon:",
        *(kept or ["(none yet)"]),
        "",
        "New story:",
        f'{new.claim} (it said: "{new.quote}")',
    ]
    return "\n".join(text), refs


def parse_canon(data: Json, refs: Mapping[str, StoryId]) -> CanonRead | None:
    """One verdict. None for an answer of the wrong shape. `same` without a kept story is the same
    as the sheet, which is canon already: it fits. Read as unreadable, it stopped the queue for good
    on a story the sheet already tells (2026-10-26)."""
    if not isinstance(data, dict):
        return None
    verdict, label = data.get("verdict"), str(data.get("story") or "").strip("[] ")
    if verdict not in set(Verdict):
        return None
    v = Verdict(str(verdict))
    of = refs.get(label) if v in {Verdict.SAME, Verdict.CONTRADICTS} else None
    if v is Verdict.SAME and of is None:
        return CanonRead(Verdict.FITS, None)
    return CanonRead(v, of)


# A read that objects keeps a story out of canon; when reads object differently, the first here wins
# a tie.
_OBJECTIONS = (Verdict.TOO_BIG, Verdict.CONTRADICTS, Verdict.NOT_A_STORY)


def rule(reads: Sequence[CanonRead | None], claims: Mapping[StoryId, str]) -> Ruling | None:
    """Its standing from the reads, or None when any read failed (it waits for the next pass).
    Canon needs no read to object; any objection keeps it out with the commonest objection's
    reason. Otherwise most reads naming the same kept story make it evidence of that story."""
    if not reads or any(r is None for r in reads):
        return None
    got = [r for r in reads if r is not None]
    objected = Counter(r.verdict for r in got if r.verdict in _OBJECTIONS)
    if objected:
        top = max(objected.values())
        verdict = next(v for v in _OBJECTIONS if objected[v] == top)
        of = _commonest(r.of for r in got if r.verdict is verdict)
        return Ruling(Standing.NOT_CANON, verdict, of, _why(verdict, of, claims))
    same = Counter(r.of for r in got if r.verdict is Verdict.SAME and r.of is not None)
    if same and (top := same.most_common(1)[0])[1] * 2 > len(got):
        of = top[0]
        return Ruling(
            Standing.EVIDENCE, Verdict.SAME, of, f"the same story as {of[:8]}, kept as a telling"
        )
    return Ruling(Standing.CANON, Verdict.FITS, None, "fits the sheet and the stories kept so far")


def _commonest(ids: Iterable[StoryId | None]) -> StoryId | None:
    found = Counter(i for i in ids if i is not None)
    return found.most_common(1)[0][0] if found else None


def _why(verdict: Verdict, of: StoryId | None, claims: Mapping[StoryId, str]) -> str:
    match verdict:
        case Verdict.TOO_BIG:
            return "a big life event the character sheet does not have"
        case Verdict.CONTRADICTS if of is not None:
            return f'contradicts {of[:8]} ("{claims.get(of, "")}")'
        case Verdict.CONTRADICTS:
            return "contradicts the character sheet"
        case _:
            return "not a story about its own past"
