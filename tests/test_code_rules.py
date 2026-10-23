"""Rules from AGENTS.md kept as checks, so the code cannot drift from them (architecture audit,
2026-10-23). A limit here only ever moves down: when a file shrinks, lower its cap."""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "companion"

# Matching a logged reason's text is how look-ups broke before decisions had keys. These are the
# only places allowed: the key fallback itself, a route decision from before its detail was kept,
# and belief closure reasons, which have no keys.
REASON_MATCH = re.compile(r"reason\.(startswith|endswith)\(")
REASON_ALLOWED = {"core/types.py": 1, "loops/route.py": 1, "loops/calibrate.py": 1}

# No new god files: a file over DEFAULT_CAP lines is split. The big ones may only shrink.
DEFAULT_CAP = 450
CAPS = {
    "loops/fast.py": 286,
    "loops/notes.py": 708,
    "daemon.py": 572,
    "store/sqlite/store.py": 537,
}
NOQA_CAP = 66  # lint exceptions in src; each new one replaces an old one


def _sources() -> dict[str, str]:
    return {
        str(p.relative_to(SRC)): p.read_text(encoding="utf-8")
        for p in sorted(SRC.rglob("*.py"))
        if "__pycache__" not in p.parts
    }


def test_no_code_matches_a_decisions_reason_text() -> None:
    found = {
        name: len(REASON_MATCH.findall(text))
        for name, text in _sources().items()
        if REASON_MATCH.search(text)
    }
    extra = {n: c for n, c in found.items() if c > REASON_ALLOWED.get(n, 0)}
    assert not extra, f"match a decision's key (Decision.has_key), not its reason text: {extra}"


def test_no_file_grows_past_its_cap() -> None:
    over = {
        name: lines
        for name, text in _sources().items()
        if (lines := text.count("\n")) > CAPS.get(name, DEFAULT_CAP)
    }
    assert not over, f"split these files instead of growing them: {over}"


def test_lint_exceptions_do_not_pile_up() -> None:
    count = sum(text.count("# noqa") for text in _sources().values())
    assert count <= NOQA_CAP, f"{count} noqa comments in src, the cap is {NOQA_CAP}"
