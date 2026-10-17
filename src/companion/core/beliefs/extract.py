"""Turn a window of conversation into candidate beliefs, then gate each one.

The model proposes. Code disposes: a candidate becomes a Belief only if its quote occurs verbatim
in a user utterance and the result satisfies every Belief invariant. Everything else is a logged
rejection, never a silent drop.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, tzinfo
from typing import cast

from companion.core.beliefs.verify import QuoteNotFoundError, evidence_from
from companion.core.clock import utc_now
from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
    Evidence,
    Frame,
    Json,
    Provenance,
    RelationshipId,
    Speaker,
    Subject,
    Utterance,
    UtteranceId,
)

SINGLE_EVIDENCE_CONFIDENCE_CAP = 0.6
MIN_CONFIDENCE = 0.4
# The model's "lasting" call is unreliable (it has marked loneliness and a project start date as
# momentary). Dropping a real disclosure costs more than keeping a noisy belief, so the filter
# applies only to low-sensitivity states and preferences, where the noise is, and never to events,
# threads, habits or anything sensitive.
MOMENTARY_KINDS = frozenset({BeliefKind.STATE, BeliefKind.PREFERENCE})
SENSITIVE = 2
# What the user plainly says about themselves in a romantic or sexual setting may be kept. What the
# model concludes from how they behave in the chat (a tell, an event, a state) may not.
ROMANTIC_KINDS = frozenset({BeliefKind.TRAIT, BeliefKind.PREFERENCE, BeliefKind.BOUNDARY})
MODEL_PROVENANCE = frozenset(
    {
        Provenance.STATED,
        Provenance.INFERRED,
        Provenance.JOKED,
        Provenance.PLAYED,
        Provenance.HYPOTHETICAL,
        Provenance.THIRD_PARTY,
    }
)
USER_SUBJECTS = frozenset({Subject.USER, Subject.RELATIONSHIP, Subject.WORLD})

SYSTEM = """You read a chat between a person (USER) and their companion (COMPANION) and record \
what the USER revealed about themselves. You are a careful note-taker, not a therapist.

Record only things the USER said in the messages marked TARGET. Use the other messages only to \
understand them. Never record anything the COMPANION said as a fact about the user.

Each message has a label in brackets, such as m3. For each belief give the label of the message \
and an exact quote: copy a contiguous run of words from that TARGET message, character for \
character. Do not paraphrase, fix typos or join separate sentences. If you cannot quote it, do \
not record it.

Kinds: trait (stable about them), state (true now, may change), event (something that happened), \
preference (likes, dislikes, how they want things), thread (an ongoing situation or project), \
boundary (something they ask the companion to do or stop doing), tell (a habit or pattern in how \
they behave), promise (something the companion committed to do).

Provenance: stated (they said it plainly about themselves), inferred (you read it between the \
lines; use sparingly), joked (said as a joke or tease), played (said inside pretend or roleplay), \
hypothetical (an if or what-if), third_party (about someone else).

Sensitivity: 0 ordinary, 1 personal, 2 health, body (appearance, measurements), mental health, \
money, relationships or identity (gender, sexuality, religion, politics), 3 abuse, crisis or \
legal trouble.

Write every claim so it stands alone, as if read a year later by someone who never saw this \
chat. Replace relative times (last night, yesterday, lately, this week, now, currently, the night \
before) with absolute dates worked out from that message's own timestamp, for example "on \
2026-10-14" or "as of 2026-10-15" for a state with no clear start. Times are in the user's local \
timezone. Replace vague references (it, that, this, you) with what they refer to. The COMPANION is \
the AI the user is chatting with. When the user says "you", they mean the companion, so write \
"the companion".

Label every candidate romantic as true when it is about romantic, flirtatious or sexual \
behaviour or play between the USER and the COMPANION in this chat (who invited what, who pushed, \
who declined, how far a scene went, what the user did in a scene), and false for anything else. \
Such behaviour is not recorded as a fact about the user's life. Only what the user plainly says \
about themselves in that setting (a preference or a boundary they state, such as what they do or \
do not want) is kept, so mark it stated and do not draw conclusions from their behaviour.

If a TARGET message restates something already recorded, do not write a new belief. Add a \
candidate with `confirms` set to that recorded belief's label (for example k2), the message \
label and an exact quote of the restatement, and the same claim. Leave `confirms` empty for \
anything new. A restatement keeps a belief fresh.

A message marked [play], [story] or [hypothetical] is pretend, fiction or a what-if, not real \
life. Record nothing from it as fact about the user.

Stay close to their words. Do not add feelings, motives or conclusions they did not state; if you \
are reading between the lines, the provenance is inferred. A self-deprecating joke is joked, not \
stated. Set lasting to false only for momentary things: what they want to eat or do this minute, a \
passing mood, small talk, polite reassurance. When something started or happened is lasting, and \
so are habits and coping patterns (a tell); record those. Confidence is how sure you \
are the claim is true and still current, from 0 to 1. Skip greetings and one-word replies. \
Do not record routine events of the day such as meals, errands or deliveries. Record what they \
mean, not their literal words: if the phrasing is a figure of speech or easy to misread ("i'm so \
bad at getting distracted" means they get distracted easily), state the meaning. Fewer, true \
beliefs beat many guesses. If there is nothing worth recording, return an empty \
list. Write each claim as one short plain sentence about the user, in the third person."""

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "beliefs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ref": {"type": "string"},
                    "quote": {"type": "string"},
                    "claim": {"type": "string"},
                    "subject": {"type": "string", "enum": ["user", "relationship", "world"]},
                    "kind": {"type": "string", "enum": [k.value for k in BeliefKind]},
                    "provenance": {"type": "string", "enum": [p.value for p in MODEL_PROVENANCE]},
                    "confidence": {"type": "number"},
                    "lasting": {"type": "boolean"},
                    "romantic": {"type": "boolean"},
                    "sensitivity": {"type": "integer"},
                    "confirms": {"type": "string"},
                },
                "required": [
                    "ref",
                    "quote",
                    "claim",
                    "subject",
                    "kind",
                    "provenance",
                    "confidence",
                    "lasting",
                    "romantic",
                    "sensitivity",
                ],
            },
        }
    },
    "required": ["beliefs"],
}


@dataclass(frozen=True, slots=True)
class Candidate:
    ref: str
    quote: str
    claim: str
    subject: Subject
    kind: BeliefKind
    provenance: Provenance
    confidence: float
    sensitivity: int
    lasting: bool = True
    confirms: str = ""
    grounding: str = ""
    romantic: bool = False  # about romantic, flirtatious or sexual behaviour in the chat
    stance: str = ""  # a view only: holds_view, commits or declines
    prompted: bool = False  # a view only: said in reply to a request or a push from the user


@dataclass(frozen=True, slots=True)
class Rejection:
    reason: str
    raw: Json


def index_window(window: Sequence[Utterance]) -> dict[str, Utterance]:
    """Short labels (m1, m2, ...) the model can copy without error, mapped to real utterances."""
    return {f"m{i}": u for i, u in enumerate(window, start=1)}


def known_index(known: Sequence[Belief]) -> dict[str, Belief]:
    """Short labels (k1, k2, ...) for recorded beliefs, so a restatement can point at one."""
    return {f"k{i}": b for i, b in enumerate(known, start=1)}


def build_user_prompt(
    index: Mapping[str, Utterance],
    targets: set[UtteranceId],
    known: Mapping[str, Belief],
    tz: tzinfo = UTC,
    rejected: Sequence[Belief] = (),
) -> str:
    lines: list[str] = []
    for label, u in index.items():
        who = "USER" if u.speaker is Speaker.USER else "COMPANION"
        mark = " TARGET" if u.id in targets else ""
        stamp = u.at.astimezone(tz).strftime("%a %Y-%m-%d %H:%M")
        scene = "" if u.frame is Frame.REAL else f" [{u.frame.value}]"
        lines.append(f"[{label}] {who}{mark}{scene} ({stamp}): {u.text}")
    offset = utc_now().astimezone(tz).strftime("%z")
    out = [f"Conversation (times are local, UTC{offset}):", *lines]
    if known:
        out += ["", "Already recorded:", *[f"[{label}] {b.claim}" for label, b in known.items()]]
    if rejected:
        out += [
            "",
            "Rejected by the user. Never record these or anything like them:",
            *[f"- {b.claim}" for b in rejected],
        ]
    return "\n".join(out)


def _obj(value: Json) -> dict[str, Json] | None:
    return cast("dict[str, Json]", value) if isinstance(value, dict) else None


def _list(value: Json) -> list[Json] | None:
    return cast("list[Json]", value) if isinstance(value, list) else None


def parse(data: Json) -> tuple[list[Candidate], list[Rejection]]:
    """Malformed items become rejections. A malformed whole yields one rejection and no items."""
    top = _obj(data)
    items = _list(top.get("beliefs")) if top is not None else None
    if items is None:
        return [], [Rejection("response did not match the schema", data)]
    ok: list[Candidate] = []
    bad: list[Rejection] = []
    for item in items:
        fields = _obj(item)
        try:
            if fields is None:
                msg = "item is not an object"
                raise ValueError(msg)
            ok.append(
                Candidate(
                    ref=str(fields.get("ref")).strip(),
                    quote=str(fields.get("quote")),
                    claim=str(fields.get("claim")).strip(),
                    subject=Subject(str(fields.get("subject"))),
                    kind=BeliefKind(str(fields.get("kind"))),
                    provenance=Provenance(str(fields.get("provenance"))),
                    confidence=_number(fields.get("confidence")),
                    sensitivity=int(_number(fields.get("sensitivity"))),
                    lasting=fields.get("lasting") is not False,
                    confirms=str(fields.get("confirms") or "").strip(),
                    grounding=str(fields.get("grounding") or "").strip(),
                    romantic=fields.get("romantic") is True,
                    stance=str(fields.get("stance") or "").strip(),
                    prompted=fields.get("prompted") is True,
                )
            )
        except ValueError as err:
            bad.append(Rejection(f"malformed candidate: {err}", item))
    return ok, bad


def _number(value: Json) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"expected a number, got {value!r}"
        raise ValueError(msg)
    return float(value)


def normalise(claim: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", claim.lower()).strip()


def _resolve(
    c: Candidate, index: Mapping[str, Utterance], speaker: Speaker = Speaker.USER
) -> Utterance | None:
    """The cited message, or failing that the one message by `speaker` that contains the quote.

    The quote is verified afterwards either way, so the fallback cannot admit anything the
    label would not have. It only rescues a good quote that cites a garbled label.
    """
    cited = index.get(c.ref)
    if cited is not None:
        return cited
    holders = [u for u in index.values() if u.speaker is speaker and _holds(u, c.quote)]
    return holders[0] if len(holders) == 1 else None


def _holds(u: Utterance, quote: str) -> bool:
    try:
        evidence_from(u, quote)
    except QuoteNotFoundError:
        return False
    return True


def _screen(c: Candidate, source: Utterance | None) -> str | None:
    """Why this candidate must not become a belief, or None if it passes the cheap checks."""
    if source is None:
        return "cited message not found and no single message holds the quote"
    romantic_kept = c.provenance is Provenance.STATED and c.kind in ROMANTIC_KINDS
    checks = (
        (source.speaker is not Speaker.USER, "evidence is the companion's own words"),
        (
            not c.lasting and c.kind in MOMENTARY_KINDS and c.sensitivity < SENSITIVE,
            "momentary, not lasting",
        ),
        (c.confidence < MIN_CONFIDENCE, "too uncertain to record"),
        (
            c.subject not in USER_SUBJECTS or c.provenance not in MODEL_PROVENANCE,
            "subject or provenance not allowed from the model",
        ),
        (
            c.romantic and not romantic_kept,
            "romantic or sexual behaviour in the chat is not recorded as a belief about them",
        ),
    )
    return next((message for failed, message in checks if failed), None)


def to_belief(
    c: Candidate,
    index: Mapping[str, Utterance],
    relationship_id: RelationshipId,
    now: datetime,
    new_id: Callable[[], str],
) -> Belief | Rejection:
    raw: Json = {"claim": c.claim, "quote": c.quote, "ref": c.ref}
    source = _resolve(c, index)
    reason = _screen(c, source)
    if reason is not None or source is None:
        return Rejection(reason or "no source", raw)
    try:
        evidence = evidence_from(source, c.quote)
    except QuoteNotFoundError:
        return Rejection("quote is not verbatim in the source utterance", raw)
    try:
        return Belief(
            id=BeliefId(new_id()),
            relationship_id=relationship_id,
            subject=c.subject,
            kind=c.kind,
            claim=c.claim,
            evidence=(evidence,),
            provenance=c.provenance,
            speaker=source.speaker,
            frame=source.frame,
            confidence=min(c.confidence, SINGLE_EVIDENCE_CONFIDENCE_CAP),
            valid_from=source.at,
            recorded_at=now,
            sensitivity=min(max(c.sensitivity, 0), 3),
        )
    except ValueError as err:
        return Rejection(f"violates a belief invariant: {err}", raw)


@dataclass(frozen=True, slots=True)
class Confirmation:
    """New support for a belief that already exists. The quote has been verified."""

    belief: Belief
    evidence: Evidence


@dataclass(frozen=True, slots=True)
class Skip:
    """Nothing to do, and nothing wrong."""

    reason: str


def _confirmation_problem(
    source: Utterance | None, belief: Belief | None, speaker: Speaker
) -> str | None:
    if belief is None:
        return "confirms a belief that is not on the recorded list"
    if source is None:
        return "cited message not found and no single message holds the quote"
    if source.speaker is not speaker or source.speaker is not belief.speaker:
        return "a restatement must be the same speaker's own words, like the belief"
    if source.frame is not belief.frame:
        return "a restatement in a different frame is not the same evidence"
    return None


def to_confirmation(
    c: Candidate,
    index: Mapping[str, Utterance],
    known: Mapping[str, Belief],
    speaker: Speaker = Speaker.USER,
) -> Confirmation | Rejection | Skip:
    raw: Json = {"claim": c.claim, "quote": c.quote, "ref": c.ref, "confirms": c.confirms}
    belief = known.get(c.confirms)
    source = _resolve(c, index, speaker)
    problem = _confirmation_problem(source, belief, speaker)
    if problem is not None or belief is None or source is None:
        return Rejection(problem or "nothing to confirm", raw)
    try:
        evidence = evidence_from(source, c.quote)
    except QuoteNotFoundError:
        return Rejection("quote is not verbatim in the source utterance", raw)
    if any(e.utterance_id == source.id for e in belief.evidence):
        return Skip("that message already supports this belief")
    return Confirmation(belief, evidence)
