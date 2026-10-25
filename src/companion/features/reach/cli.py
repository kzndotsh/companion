"""The part of `companion initiative` about reaching out for its own reasons (ADR 0021): their
learned rhythm and how much of it is the baseline, the share of conversations it starts against the
dial, each would-send with its time, kind and draft, the dropped drafts, and the holds by reason."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, tzinfo

from companion.core.types import DecisionKind, RelationshipId
from companion.features.reach.gate import Hold
from companion.features.reach.logic import HELD, PACED, TARGET, Dial
from companion.features.reach.run import Reacher, situation
from companion.store.sqlite.store import Store


def _hours(hours: frozenset[int]) -> str:
    return ", ".join(f"{h}:00" for h in sorted(hours)) or "none"


def _dial(store: Store, rel: RelationshipId, fallback: Dial) -> Dial:
    """The dial the bot last ran with, from its newest record; the setting here when none."""
    held = [d for d in store.decisions_of_kind(rel, DecisionKind.DO_NOTHING) if d.has_key(HELD)]
    newest = [(d.at, (d.detail or {}).get("dial")) for d in held]
    newest += [(o.at, o.detail.get("dial")) for o in store.own_reach_outs(rel)]
    found = max(newest, key=lambda n: n[0], default=(None, None))[1]
    return Dial(found) if isinstance(found, str) and found in set(Dial) else fallback


def lines(
    store: Store, rel: RelationshipId, when: tuple[datetime, tzinfo], setting: Dial
) -> list[str]:
    tz = when[1]
    dial = _dial(store, rel, setting)
    sit, look = situation(store, rel, when, Reacher(dial, None))
    r = sit.rhythm
    learned = "none yet" if r.learned_pause is None else f"{r.learned_pause:.1f}h"
    kept = look.kept
    weight = f"{r.weight:.0%} theirs and {1 - r.weight:.0%} baseline"
    pause = f"their 75th percentile pause {learned}, baseline 12h, never under 8h"
    out = [
        f"reaching out for its own reasons (shadow), COMPANION_REACH {dial.value}",
        f"  their rhythm: {r.conversations} conversations in two weeks, {weight}",
        f"  missing them after {r.pause:.1f}h ({pause})",
        f"  usual hours: {_hours(r.usual)}",
        f"  quiet hours: {_hours(r.quiet)}",
        f"  a time they keep: {'none' if kept is None else f'{kept}:00'}",
        f"  share it started: {sit.share.mine} of {sit.share.total}"
        f" ({sit.share.value:.2f}) against {sit.effective.value} ({TARGET[sit.effective]:.2f})"
        + (f"; a step down: {sit.paced}" if sit.paced else ""),
        "",
        "its own reach-outs (would have sent)",
    ]
    own = store.own_reach_outs(rel)
    out += [
        f"  {o.at.astimezone(tz):%m-%d %H:%M}  {o.kind:16} {o.draft}"
        for o in own
        if o.mode != "dropped"
    ] or ["  none yet"]
    dropped = [o for o in own if o.mode == "dropped"]
    out += ["", f"drafts dropped by the check ({len(dropped)})"]
    out += [
        f"  {o.at.astimezone(tz):%m-%d %H:%M}  {o.kind:16} {o.detail.get('drafted') or '(none)'}"
        for o in dropped
    ] or ["  none"]
    held = [d for d in store.decisions_of_kind(rel, DecisionKind.DO_NOTHING) if d.has_key(HELD)]
    counts = Counter(str((d.detail or {}).get("hold", "")) for d in held)
    out += ["", "holds by reason (each counted once while it lasted)"]
    out += [f"  {counts[h.value]:4}  {h.value}" for h in Hold if counts[h.value]] or ["  none"]
    paced = [d for d in store.decisions_of_kind(rel, DecisionKind.POLICY) if d.has_key(PACED)]
    out += [f"  dial stepped down {len(paced)} times"] if paced else []
    return out
