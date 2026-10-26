"""`companion history`: the stories of its own past it made up in chat (ADR 0025): canon with how
many times it told each, the ones kept as a telling of an earlier story, the ones not canon with
the reason, and the ones waiting for the check. `companion retire ID` retires one."""

from __future__ import annotations

import uuid
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.types import RelationshipId, TraceId
from companion.features.history.logic import Recorded, Ruling, Standing
from companion.features.history.store import By
from companion.loops.record import Recorder
from companion.store.sqlite.store import Store

RETIRED = "history: the owner retired a story"


def _line(r: Recorded) -> str:
    head = f'{r.story.id[:8]}  {r.story.claim}\n    "{r.story.quote}"'
    scene = "" if r.story.frame.value == "real" else f" [{r.story.frame.value}]"
    match r.standing:
        case Standing.CANON:
            return f"{head}{scene}\n    told {len(r.told)}x, last {r.last_told:%Y-%m-%d}"
        case Standing.EVIDENCE | Standing.NOT_CANON | Standing.RETIRED:
            return f"{head}{scene}\n    {r.reason}"
        case None:
            return f"{head}{scene}"


_SECTIONS = (
    (Standing.CANON, "canon"),
    (None, "waiting for the canon check"),
    (Standing.EVIDENCE, "told again (kept as a telling of an earlier story)"),
    (Standing.NOT_CANON, "not canon"),
    (Standing.RETIRED, "retired"),
)


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    try:
        stories = store.stories().recorded(RelationshipId(relationship))
    finally:
        store.close()
    if not stories:
        return "no stories of its own past yet\n"
    out: list[str] = []
    for standing, title in _SECTIONS:
        group = [r for r in reversed(stories) if r.standing is standing]
        if group:
            out += [f"{title} ({len(group)}):", *(_line(r) for r in group), ""]
    return "\n".join(out)


def retire_story(store: Store, rel: RelationshipId, id_prefix: str, reason: str) -> str | None:
    """Retire the one story whose id starts with the prefix, logged with the reason. None when no
    story matches, so the caller can say so."""
    matches = [
        r
        for r in store.stories().recorded(rel)
        if r.story.id.startswith(id_prefix) and r.standing is not Standing.RETIRED
    ]
    if not matches:
        return None
    if len(matches) > 1:
        msg = f"{len(matches)} stories start with {id_prefix!r}; need exactly one"
        raise ValueError(msg)
    story = matches[0].story
    now = utc_now()
    store.stories().rule(
        story.id, Ruling(Standing.RETIRED, None, None, reason), By("owner", "", now)
    )
    source = store.get_utterance(story.utterance_id)
    if source is not None:
        Recorder(
            store, rel, source.session_id, source.turn_id, TraceId(uuid.uuid4().hex), now
        ).decide(
            RETIRED, {"story_id": story.id, "claim": story.claim}, reason=f"{RETIRED}: {reason}"
        )
    return f"retired  {story.claim}"
