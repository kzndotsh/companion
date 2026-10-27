"""A separate memory lane for intimate scenes (ADR 0026): which memories belong to it, and the card
a scene turn gets instead of the everyday one.

Every memory about them gets a lane, read three times: everyday or intimate, and for an intimate
one its stance. A memory is intimate only when all three reads agree on the lane and the stance;
any disagreement keeps it out of scenes (`Why.DOUBT`). Above the reads sits a floor in code that no
label moves (`screen`): nothing that touches age, minors, school or an age-regression headspace,
nothing from a turn the minor check held, nothing crisis-level, nothing said while they were
sharing something heavy, and no limit that is not in their own plain words.

Patterns of how they play are noted scene by scene and become an entry only once seen in two
separate scenes. They are never limits.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from companion.core.frames import SCENE_GAP
from companion.core.types import (
    Belief,
    BeliefId,
    Frame,
    Json,
    Provenance,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.prompts import get

LANE = get("system/scene-lane")
PATTERN = get("system/scene-pattern")
LIMITS_NOTE = get("notes/scene-limits")
KNOWN_NOTE = get("notes/scene-known")
OFFER_NOTE = get("notes/scene-offer")
BASICS_NOTE = get("notes/scene-basics")

BATCH = 60  # memories labelled per call
NEAREST = 3  # entries nearest the moment on a scene card, besides the limits
MIN_SCENES = 2  # a pattern is an entry only once seen in this many separate scenes
COOL = timedelta(days=3)  # a curious item they pushed back is not offered again this soon
CRISIS = 3  # the top sensitivity: never in a scene


class Lane(StrEnum):
    EVERYDAY = "everyday"
    INTIMATE = "intimate"
    EXCLUDED = "excluded"


class Stance(StrEnum):
    INTO = "into"
    CURIOUS = "curious"
    SOFT_LIMIT = "soft_limit"
    HARD_LIMIT = "hard_limit"
    STYLE = "style"
    AFTERCARE = "aftercare"


LIMITS = (Stance.HARD_LIMIT, Stance.SOFT_LIMIT)  # pinned first, hard before soft
PATTERN_STANCES = frozenset({Stance.INTO, Stance.STYLE, Stance.CURIOUS})
KNOWN_STANCES = frozenset({Stance.INTO, Stance.STYLE, Stance.AFTERCARE})


class Why(StrEnum):
    """Why a memory is kept out of scenes."""

    DOUBT = "doubt"
    FLOOR = "floor"
    CRISIS = "crisis"
    LISTENING = "listening"
    NOT_THEIR_WORDS = "not_their_words"


WHY_TEXT = {
    Why.DOUBT: "the three reads did not agree",
    Why.FLOOR: "excluded by the floor",
    Why.CRISIS: "crisis-level sensitivity",
    Why.LISTENING: "said while they were sharing something heavy",
    Why.NOT_THEIR_WORDS: "a limit not in their own plain words",
}


@dataclass(frozen=True, slots=True)
class Everyday:
    pass


@dataclass(frozen=True, slots=True)
class Intimate:
    stance: Stance


@dataclass(frozen=True, slots=True)
class Excluded:
    why: Why


type Place = Everyday | Intimate | Excluded
type Vote = Everyday | Intimate  # what one read says of one memory


def lane_of(p: Place) -> Lane:
    match p:
        case Everyday():
            return Lane.EVERYDAY
        case Intimate():
            return Lane.INTIMATE
        case Excluded():
            return Lane.EXCLUDED


# Conservative on purpose: a false match only keeps a memory out of scenes. "little" is matched
# alone because the headspace is named with it; that also drops a phrase such as "a little rough".
# A number under 18 counts unless it is part of a date, since claims carry absolute dates.
_AGE = re.compile(
    r"\b(?:ages?|aged|years?[- ]?olds?|y/?o|minors?|under[- ]?age\w*|child\w*|kids?|kiddo"
    r"|teen\w*|young\w*|youth|juvenile|school\w*|student\w*|pupils?|classroom|babysit\w*"
    r"|littles?|littlespace|regress\w*|ageplay|age[- ]play\w*|ddlg|mdlg|cgl|abdl|diapers?"
    r"|pacifiers?)\b|(?<![\d/:-])(?:1[0-7]|[1-9])(?![\d/:-])",
    re.IGNORECASE,
)


def touches_age(*texts: str) -> bool:
    """Whether any text touches age, minors, school or an age-regression headspace."""
    return any(_AGE.search(t) for t in texts)


@dataclass(frozen=True, slots=True)
class Facts:
    """What the turns a memory came from say about it: the minor check held one of them, or one was
    read as serious (severity 2 or more) while they were sharing."""

    held: bool = False
    heavy: bool = False


def screen(vote: Place, b: Belief, facts: Facts) -> Place:
    """The floor over a belief's agreed lane. An everyday memory stays everyday. An intimate or
    doubtful one that touches age, or came from a turn the minor check held, is the floor's; an
    intimate one is also kept out when crisis-level, said while sharing something heavy, or a limit
    not in their own plain words."""
    if isinstance(vote, Everyday):
        return vote
    if facts.held or touches_age(b.claim, *(e.quote for e in b.evidence)):
        return Excluded(Why.FLOOR)
    if isinstance(vote, Excluded):
        return vote
    checks = (
        (b.sensitivity >= CRISIS, Why.CRISIS),
        (facts.heavy, Why.LISTENING),
        (vote.stance in LIMITS and not _own_plain_words(b), Why.NOT_THEIR_WORDS),
    )
    why = next((w for failed, w in checks if failed), None)
    return vote if why is None else Excluded(why)


def _own_plain_words(b: Belief) -> bool:
    return b.provenance is Provenance.STATED and b.frame is Frame.REAL and b.speaker is Speaker.USER


LANE_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "labels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ref": {"type": "string"},
                    "lane": {"type": "string", "enum": [Lane.EVERYDAY, Lane.INTIMATE]},
                    "stance": {"type": "string", "enum": [*(s.value for s in Stance), "none"]},
                },
                "required": ["ref", "lane", "stance"],
            },
        }
    },
    "required": ["labels"],
}


def lane_prompt(beliefs: Iterable[Belief]) -> tuple[str, dict[str, BeliefId]]:
    """Each memory under a short ref with the words they said, and the refs back to their ids."""
    listed = list(beliefs)
    refs = {f"b{n}": b.id for n, b in enumerate(listed, 1)}
    lines = [
        f'[{ref}] {b.claim} (they said: "{b.evidence[0].quote}")'
        for ref, b in zip(refs, listed, strict=True)
    ]
    return "\n".join(lines), refs


def parse_lanes(data: Json, refs: Mapping[str, BeliefId]) -> dict[BeliefId, Vote] | None:
    """One read's vote per memory it was shown. An intimate vote with no stance is no vote. None for
    an answer of the wrong shape."""
    items = data.get("labels") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    out: dict[BeliefId, Vote] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        bid = refs.get(str(item.get("ref", "")).strip("[] "))
        lane, stance = item.get("lane"), item.get("stance")
        if bid is None or bid in out:
            continue
        if lane == Lane.EVERYDAY:
            out[bid] = Everyday()
        elif lane == Lane.INTIMATE and stance in set(Stance):
            out[bid] = Intimate(Stance(str(stance)))
    return out


def agree(
    reads: Sequence[Mapping[BeliefId, Vote]], shown: Iterable[BeliefId]
) -> dict[BeliefId, Place]:
    """One place per memory from the reads: the lane and stance every read gave, else doubt. A read
    that left a memory out is doubt too."""
    out: dict[BeliefId, Place] = {}
    for bid in shown:
        votes = [r.get(bid) for r in reads]
        first = votes[0] if votes else None
        same = first is not None and all(v == first for v in votes)
        out[bid] = first if same and first is not None else Excluded(Why.DOUBT)
    return out


@dataclass(frozen=True, slots=True)
class Entry:
    """One thing a scene card may show: an intimate memory, or a pattern seen in enough scenes."""

    id: str
    claim: str
    stance: Stance
    quotes: tuple[str, ...]
    scenes: int = 0  # separate scenes it was seen in; 0 for a memory they told outside a scene

    @property
    def pattern(self) -> bool:
        return self.scenes > 0


# --- Scenes and the patterns read from them ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class Scene:
    key: UtteranceId  # its first message
    messages: tuple[Utterance, ...]

    @property
    def turns(self) -> frozenset[TurnId]:
        return frozenset(u.turn_id for u in self.messages)


def scenes(messages: Sequence[Utterance]) -> list[Scene]:
    """The pretend scenes in a run of messages, oldest first. A scene starts at a message of theirs
    in play and holds the replies that follow; it ends at a message of theirs that is not play, or
    after a gap of SCENE_GAP (as `core/frames.py` ends one)."""
    out: list[list[Utterance]] = []
    current: list[Utterance] | None = None
    for u in messages:
        if current is not None and u.at - current[-1].at >= SCENE_GAP:
            current = None
        if u.speaker is Speaker.USER:
            if u.frame is not Frame.PLAY:
                current = None
                continue
            if current is None:
                current = []
                out.append(current)
        if current is not None:
            current.append(u)
    return [Scene(s[0].id, tuple(s)) for s in out]


@dataclass(frozen=True, slots=True)
class Quote:
    scene: UtteranceId  # the scene's key
    utterance: UtteranceId
    text: str


@dataclass(frozen=True, slots=True)
class Pattern:
    id: str
    claim: str
    stance: Stance
    quotes: tuple[Quote, ...]
    retired: bool = False

    @property
    def scenes(self) -> int:
        return len({q.scene for q in self.quotes})


def pattern_entry(p: Pattern, held: Collection[UtteranceId] = ()) -> Entry | None:
    """A pattern as a scene card entry: once seen in MIN_SCENES separate scenes, not retired, never
    a limit, and only from quotes the floor lets through (no age, no turn the minor check held)."""
    quotes = [q for q in p.quotes if q.utterance not in held and not touches_age(q.text)]
    seen = len({q.scene for q in quotes})
    if p.retired or p.stance not in PATTERN_STANCES or touches_age(p.claim) or seen < MIN_SCENES:
        return None
    return Entry(p.id, p.claim, p.stance, tuple(q.text for q in quotes), seen)


def closed(scene: Scene, after: Sequence[Utterance], now: datetime) -> bool:
    """Whether a scene is over: a message of theirs out of play came after it, or it went quiet."""
    last = scene.messages[-1]
    ended = any(
        u.at > last.at and u.speaker is Speaker.USER and u.frame is not Frame.PLAY for u in after
    )
    return ended or now - last.at >= SCENE_GAP


PATTERN_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "claim": {"type": "string"},
                    "stance": {"type": "string", "enum": [s.value for s in PATTERN_STANCES]},
                    "message": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["pattern", "claim", "stance", "message", "quote"],
            },
        }
    },
    "required": ["patterns"],
}


@dataclass(frozen=True, slots=True)
class Proposed:
    pattern: str
    claim: str
    stance: str
    message: str
    quote: str


def pattern_prompt(
    known: Sequence[tuple[str, str]], scene: Scene
) -> tuple[str, dict[str, Utterance], dict[str, str]]:
    """The noted patterns under refs (p1, p2) and the scene's messages under labels (m1, m2), with
    both maps back. `known` is (pattern id, claim)."""
    refs = {f"p{n}": pid for n, (pid, _) in enumerate(known, 1)}
    labels = {f"m{n}": u for n, u in enumerate(scene.messages, 1)}
    noted = [f"[{ref}] {claim}" for ref, (_, claim) in zip(refs, known, strict=True)]
    lines = [f"[{label}] {u.speaker.value.upper()}: {u.text}" for label, u in labels.items()]
    text = "\n".join(["Patterns noted so far:", *(noted or ["(none yet)"]), "", "Scene:", *lines])
    return text, labels, refs


def parse_patterns(data: Json) -> list[Proposed] | None:
    """The proposed patterns, or None when the answer does not have the shape asked for."""
    items = data.get("patterns") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    out: list[Proposed] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        fields = [item.get(k) for k in ("pattern", "claim", "stance", "message", "quote")]
        if all(isinstance(v, str) for v in fields):
            out.append(Proposed(*(str(v).strip() for v in fields)))
    return out


def refuse(p: Proposed, labels: Mapping[str, Utterance]) -> str | None:
    """Why a proposed pattern is not kept, or None. Only their own play, quoted exactly, never a
    limit, and never anything the floor would keep out."""
    source = labels.get(p.message.strip("[] "))
    if source is None or source.speaker is not Speaker.USER or source.frame is not Frame.PLAY:
        return "not one of their own messages in the scene"
    if not p.quote or p.quote not in source.text:
        return "the quote is not in their message"
    if p.stance not in PATTERN_STANCES:
        return "a pattern is never a limit"
    if touches_age(p.claim, p.quote):
        return WHY_TEXT[Why.FLOOR]
    if not p.claim:
        return "no claim"
    return None


# --- The scene card ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SceneCard:
    limits: tuple[Entry, ...]
    nearest: tuple[tuple[Entry, float], ...]
    offer: Entry | None
    basics: tuple[str, ...]

    @property
    def empty(self) -> bool:
        return not (self.limits or self.nearest or self.offer or self.basics)


def scene_card(
    entries: Sequence[Entry],
    scores: Mapping[str, float],
    basics: Sequence[str],
    *,
    may_offer: bool,
    cooled: Collection[str] = (),
) -> SceneCard:
    """Every limit, hard first; then the entries nearest the moment that say what they are into, how
    they like it to go and what they want after; then, when it may, the one curious item nearest
    the moment that was not pushed back lately; then the basics. An entry with no score is never
    nearest, so with no look-up the card holds only the limits and the basics."""
    limits = tuple(e for stance in LIMITS for e in entries if e.stance is stance)
    scored = sorted(((e, scores[e.id]) for e in entries if e.id in scores), key=lambda x: -x[1])
    nearest = tuple((e, s) for e, s in scored if e.stance in KNOWN_STANCES)[:NEAREST]
    # Only what they said they are curious about is ever offered; a curious reading of how they
    # played is a guess, and on real scenes some read like pushing past a partner's no (2026-10-26).
    curious = [
        e for e, _ in scored if e.stance is Stance.CURIOUS and not e.pattern and e.id not in cooled
    ]
    offer = curious[0] if may_offer and curious else None
    return SceneCard(limits, nearest, offer, tuple(basics))


_LIMIT_WORDS = {Stance.HARD_LIMIT: "hard limit", Stance.SOFT_LIMIT: "soft limit"}


def render_scene(card: SceneCard) -> str:
    """The scene card as bracketed blocks for the system block, in the card's order."""
    parts: list[str] = []
    if card.limits:
        items = "\n".join(f"- {_LIMIT_WORDS[e.stance]}: {e.claim}" for e in card.limits)
        parts.append(LIMITS_NOTE.render(items=items))
    if card.nearest:
        parts.append(KNOWN_NOTE.render(items="\n".join(f"- {e.claim}" for e, _ in card.nearest)))
    if card.offer is not None:
        parts.append(OFFER_NOTE.render(items=f"- {card.offer.claim}"))
    if card.basics:
        parts.append(BASICS_NOTE.render(items="\n".join(f"- {b}" for b in card.basics)))
    return "\n".join(parts)


@dataclass(frozen=True, slots=True)
class Offered:
    at: datetime
    turn: TurnId
    entry: str


@dataclass(frozen=True, slots=True)
class BrushRead:
    at: datetime
    turn: TurnId
    declined: bool


def cooled(offers: Sequence[Offered], reads: Sequence[BrushRead], now: datetime) -> frozenset[str]:
    """The curious items offered in the last COOL days that they pushed back: the first brush-off
    read on a later turn after the offer said they declined."""
    out: set[str] = set()
    for o in offers:
        if now - o.at > COOL:
            continue
        after = sorted((r for r in reads if r.at >= o.at and r.turn != o.turn), key=lambda r: r.at)
        if after and after[0].declined:
            out.add(o.entry)
    return frozenset(out)
