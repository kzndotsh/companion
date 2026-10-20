"""`companion promises`: the promises the companion made in its own replies (J12, shadow), newest
first. `--not ID` marks one as not a promise and `--retire ID` retires one; both are recorded, never
deleted, and a marked promise leaves the list."""

from __future__ import annotations

from pathlib import Path

from companion.core.clock import utc_now
from companion.core.types import RelationshipId
from companion.store.sqlite.store import Store

SHOWN = 30


def run(db: Path, relationship: str, *, wrong: str | None = None, retire: str | None = None) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        current = [r for r in store.promises(rel) if r.mark is None]
        if wrong or retire:
            prefix, mark = (wrong, "not_a_promise") if wrong else (retire, "retired")
            found = [r for r in current if r.promise.id.startswith(str(prefix))]
            if len(found) != 1:
                return f"{len(found)} current promises start with {prefix!r}; need exactly one\n"
            store.mark_promise(found[0].promise.id, mark, "the owner said so", utc_now())
            return f"marked {mark.replace('_', ' ')}: {found[0].promise.quote}\n"
        if not current:
            return "no promises recorded\n"
        lines: list[str] = []
        for r in reversed(current[-SHOWN:]):
            p = r.promise
            word = f"  avoid {p.avoid!r}" if p.avoid else ""
            lines.append(f"{p.id[:8]}  {p.at:%a %d %b %H:%M}  {p.kind:8}{word}\n  {p.quote}")
        return "\n".join(lines) + "\n"
    finally:
        store.close()
