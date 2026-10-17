"""The wall clock is read in one place, so tests and replays can pin the time."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "companion"
FORBIDDEN = re.compile(r"datetime\.now\(|\.utcnow\(|date\.today\(|time\.time\(")
ALLOWED = {ROOT / "core" / "clock.py"}


def test_core_and_loops_never_read_the_wall_clock_directly() -> None:
    offenders = [
        f"{path.relative_to(ROOT)}:{n}: {line.strip()}"
        for folder in ("core", "loops")
        for path in sorted((ROOT / folder).rglob("*.py"))
        if path not in ALLOWED
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if FORBIDDEN.search(line)
    ]
    assert offenders == [], "read the time through core.clock.utc_now:\n" + "\n".join(offenders)


def test_the_clock_module_is_where_the_time_is_read() -> None:
    assert FORBIDDEN.search((ROOT / "core" / "clock.py").read_text(encoding="utf-8"))
