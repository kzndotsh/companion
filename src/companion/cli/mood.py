"""`companion mood`: the mood now and what holds it up, or `--replay DAYS` to rebuild what it would
have been on each of their messages, from the same rules the bot uses. Writes nothing."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from itertools import pairwise
from pathlib import Path

from companion.core.clock import local_zone, utc_now
from companion.core.mood import WINDOW, Mood, Replayed, mood_at, reason, replay
from companion.core.types import RelationshipId
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str, replay_days: int | None, now: datetime | None = None) -> str:
    now = now or utc_now()
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        if replay_days is None:
            return _now(mood_at(store.mood_effects_since(rel, now - WINDOW), now, local_zone()))
        start = now - timedelta(days=replay_days)
        said = store.said_since(rel, start)
        times = store.times_since(rel, start - timedelta(days=1))
    finally:
        store.close()
    return _replayed(replay(said, times, local_zone()), replay_days)


def _now(mood: Mood) -> str:
    rows = [
        f"  {s.value:8} {v:.2f}  {', '.join(x.value for x in mood.sources[s]) or '-'}"
        for s, v in mood.strengths.items()
    ]
    return "\n".join(
        ["mood now (strength, what holds it up)", *rows, reason(mood, serious_now=False)]
    )


def _shown(r: Replayed) -> str:
    return " + ".join(s.value for s in r.mood.shown()) or "-"


def _replayed(rows: list[Replayed], days: int) -> str:
    if not rows:
        return f"no messages in the last {days} days"
    zone = local_zone()
    out = [f"mood replayed over {len(rows)} messages; a row when what would show changes"]
    last = None
    for r in rows:
        shown = "held (serious)" if r.line is None and r.mood.shown() else _shown(r)
        if shown != last:
            added = ",".join(e.source.value for e in r.added) or "-"
            sev = "-" if r.said.severity is None else str(r.said.severity)
            out.append(
                f"  {r.said.at.astimezone(zone):%m-%d %H:%M}  {shown:22} sev {sev} +{added:28}"
                f" {r.said.text[:50]!r}"
            )
            last = shown
    counts = Counter(s for r in rows if r.line is not None for s in r.mood.shown())
    changes = sum(1 for a, b in pairwise(rows) if _shown(a) != _shown(b))
    read = sum(r.said.severity is not None for r in rows)
    out += [
        "",
        f"read by the listening judge: {read} of {len(rows)} (unread messages add nothing)",
        "shown: "
        + (", ".join(f"{s.value} on {n}" for s, n in counts.most_common()) or "nothing")
        + f" of {len(rows)} messages",
        f"what shows changed on {changes} of {len(rows) - 1} messages",
    ]
    return "\n".join(out)
