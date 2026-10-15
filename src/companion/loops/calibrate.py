"""Compare the automatic gates with what the user actually decided about each view.

Every approval and every retirement is a labelled example of what the gates should have done. If
the gates mostly agree with the user, the default can be left on auto. If they would have let
through views the user rejected, the gates need work first.
"""

from __future__ import annotations

from dataclasses import dataclass

from companion.core.types import Belief, RelationshipId
from companion.core.views import Gates, gates
from companion.store.sqlite.store import Store

MECHANICAL = ("duplicate of", "replaced by a rebuild")
ENOUGH_TO_TRUST = 20
TRUST_PRECISION = 0.9


@dataclass(frozen=True, slots=True)
class Reviewed:
    belief: Belief
    verdict: str  # "approved" or "retired"
    gates: Gates
    days: int


def reviewed_views(store: Store, rel: RelationshipId) -> list[Reviewed]:
    approved = store.approved_views(rel)
    closures = store.closure_reasons(rel)
    days = store.evidence_days(rel, include_closed=True)
    checks = store.view_checks(rel)
    out: list[Reviewed] = []
    for b in store.self_beliefs_all(rel):
        reason = closures.get(b.id, "")
        rejected = bool(reason) and not any(m in reason for m in MECHANICAL)
        if rejected:
            verdict = "retired"
        elif b.id in approved:
            verdict = "approved"
        else:
            continue
        out.append(Reviewed(b, verdict, gates(b, days, checks), days.get(b.id, 1)))
    return out


def _why_not(g: Gates, b: Belief) -> str:
    if not g.kind_allowed:
        return f"kind {b.kind}: never installs itself"
    if not g.settled:
        return "not yet expressed on two days"
    if not g.checked:
        return "no conflict check yet"
    return "conflicts with what the user asked for" if g.conflicts else "eligible"


def report(rows: list[Reviewed]) -> str:
    if not rows:
        return (
            "nothing reviewed yet. Approve (companion approve) or retire (companion retire) some "
            "views and this compares the automatic gates with your decisions.\n"
        )
    both = [r for r in rows if r.gates.eligible and r.verdict == "approved"]
    wrong = [r for r in rows if r.gates.eligible and r.verdict == "retired"]
    missed = [r for r in rows if not r.gates.eligible and r.verdict == "approved"]
    agreed_no = [r for r in rows if not r.gates.eligible and r.verdict == "retired"]
    eligible = len(both) + len(wrong)
    lines = [
        f"reviewed {len(rows)} views: {sum(r.verdict == 'approved' for r in rows)} approved, "
        f"{sum(r.verdict == 'retired' for r in rows)} retired",
        "",
        "                          you approved   you retired",
        f"gates would adopt         {len(both):>12}   {len(wrong):>11}",
        f"gates would not adopt     {len(missed):>12}   {len(agreed_no):>11}",
        "",
    ]
    if eligible:
        lines.append(
            f"if left on auto, {len(both)} of {eligible} adopted views were ones you wanted "
            f"({len(both) / eligible:.0%})"
        )
    else:
        lines.append("the gates would not have adopted any of these yet")
    if len(rows) < ENOUGH_TO_TRUST:
        lines.append(
            f"only {len(rows)} reviewed; wait for {ENOUGH_TO_TRUST} before trusting the default"
        )
    for title, group in (
        ("would have adopted, but you retired", wrong),
        ("would have blocked, but you approved", missed),
    ):
        if group:
            lines += ["", title + ":"]
            lines += [
                f"  {r.belief.id[:8]} {r.belief.claim}  [{_why_not(r.gates, r.belief)}]"
                for r in group
            ]
    return "\n".join(lines) + "\n"
