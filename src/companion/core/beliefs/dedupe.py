"""Beliefs that rest on the same words are one belief said twice."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.beliefs.extract import normalise
from companion.core.types import Belief, UtteranceId


def quotes_overlap(a: str, b: str) -> bool:
    x, y = normalise(a), normalise(b)
    return bool(x) and bool(y) and (x in y or y in x)


def rests_on_same_words(a: Belief, b: Belief) -> bool:
    return any(
        ea.utterance_id == eb.utterance_id and quotes_overlap(ea.quote, eb.quote)
        for ea in a.evidence
        for eb in b.evidence
    )


def is_duplicate_candidate(utterance_id: UtteranceId, quote: str, known: Sequence[Belief]) -> bool:
    return any(
        e.utterance_id == utterance_id and quotes_overlap(e.quote, quote)
        for b in known
        for e in b.evidence
    )


def duplicate_groups(beliefs: Sequence[Belief]) -> list[tuple[Belief, list[Belief]]]:
    """(keep, drop...) per group. Keep the fullest claim; ties go to the earliest recorded."""
    groups: list[list[Belief]] = []
    for b in sorted(beliefs, key=lambda x: (x.recorded_at, x.id)):
        for g in groups:
            if any(rests_on_same_words(b, m) for m in g):
                g.append(b)
                break
        else:
            groups.append([b])
    out: list[tuple[Belief, list[Belief]]] = []
    for g in groups:
        if len(g) < 2:
            continue
        keep = max(g, key=lambda x: (len(x.claim), -x.recorded_at.timestamp()))
        out.append((keep, [m for m in g if m.id != keep.id]))
    return out
