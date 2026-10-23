"""`companion shadows`: every feature running in shadow, its review date, and the overdue ones."""

from __future__ import annotations

from companion.core.clock import local_zone, utc_now
from companion.core.shadows import SHADOWS, overdue


def run() -> str:
    today = utc_now().astimezone(local_zone()).date()
    late = set(overdue(today))
    lines = [f"{len(SHADOWS)} features in shadow; {len(late)} overdue for review", ""]
    for s in sorted(SHADOWS, key=lambda s: s.review_by):
        mark = "OVERDUE " if s in late else ""
        setting = f"setting {s.switch}" if s.switch else "always shadow"
        lines += [
            f"{mark}{s.review_by.isoformat()}  {s.name}",
            f"    read with {s.read_with}; {setting}",
            f"    judged on: {s.judged_on}",
        ]
    lines += [
        "",
        "at its review a feature graduates to live or is removed: either way, delete its row",
    ]
    return "\n".join(lines) + "\n"
