"""Check the companion's views against what the user has asked for, so none installs unchecked."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from companion.core.beliefs.views_conflict import SCHEMA, SYSTEM, build_prompt, parse
from companion.core.extractor import Extractor
from companion.core.types import BeliefKind, Json, RelationshipId
from companion.core.views import AUTO_KINDS, is_settled
from companion.store.sqlite.store import Store

WANT_KINDS = frozenset({BeliefKind.PREFERENCE, BeliefKind.BOUNDARY})


@dataclass(frozen=True, slots=True)
class ViewCheckResult:
    checked: int = 0
    conflicts: int = 0
    cost_usd: float = 0.0


async def check_views(
    store: Store,
    extractor: Extractor,
    rel: RelationshipId,
    now: datetime | None = None,
    *,
    recheck: bool = False,
) -> ViewCheckResult:
    """Ask once about every view that could install itself and has not been checked.

    `recheck` asks again about all of them, for when the user has just stated a new preference or
    boundary that an earlier clean check could not have known about.
    """
    now = now or datetime.now(UTC)
    days = store.evidence_days(rel)
    checks = store.view_checks(rel)
    pending = [
        b
        for b in store.self_beliefs(rel)
        if b.kind in AUTO_KINDS and is_settled(b, days) and (recheck or b.id not in checks)
    ]
    if not pending:
        return ViewCheckResult()
    wants = {
        f"k{i}": b
        for i, b in enumerate((b for b in store.user_beliefs(rel) if b.kind in WANT_KINDS), start=1)
    }
    views = {f"v{i}": b for i, b in enumerate(pending, start=1)}
    result = await extractor.extract(SYSTEM, build_prompt(views, wants), SCHEMA)
    parsed = parse(result.data)
    conflicts = 0
    for label, belief in views.items():
        check = parsed.get(label)
        if check is None:
            continue  # unparseable or missing: the view stays unchecked and so not eligible
        found = check.conflicts
        detail: dict[str, Json] = {
            "with": wants[check.with_label].claim
            if check.with_label in wants
            else check.with_label,
            "confidence": check.confidence,
            "model": result.model,
            "against": len(wants),
        }
        store.record_view_check(belief.id, conflicts=found, detail=detail, at=now)
        conflicts += found
    return ViewCheckResult(len(parsed), conflicts, result.cost_usd)
