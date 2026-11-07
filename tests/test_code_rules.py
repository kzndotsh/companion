"""Rules from AGENTS.md kept as checks, so the code cannot drift from them (architecture audit,
2026-10-23). A limit here only ever moves down: when a file shrinks, lower its cap."""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "companion"

# Matching a logged reason's text is how look-ups broke before decisions had keys. These are the
# only places allowed: the key fallback itself, a route decision from before its detail was kept,
# and a belief closure from before its detail said who made it.
REASON_MATCH = re.compile(
    r"reason[\"\])]*\.(startswith|endswith|find|index|partition|rpartition|split|"
    r"removeprefix)\("
    r"|\breason\s*(==|!=)|\bin\s+[\w.]*\breason\b|\.reason\s+(not\s+)?in\b"
    r"|re\.(match|search|fullmatch)\([^)\n]*\breason\b|\b\w+\.reason\s*=\s*\?"
)
# core/types.py: `Decision.has_key`'s fallback. turn/route.py: `routed_to_roleplay` and
# `route_because`, for a route logged before its detail was kept (2026-10).
# store/sqlite/decisions.py: a closure logged before `mechanical` was in its detail (2026-11-07).
# features/threads/store.py: a loop event from before events had a key (0040, 2026-11-07).
REASON_ALLOWED = {
    "core/types.py": 1,
    "turn/route.py": 2,
    "store/sqlite/decisions.py": 1,
    "features/threads/store.py": 1,
}

# No new god files: a file over DEFAULT_CAP lines is split. The big ones may only shrink.
DEFAULT_CAP = 600
CAPS: dict[
    str, int
] = {}  # a file that may only shrink below DEFAULT_CAP, by path under src/companion
NOQA_CAP = 64  # lint exceptions in src; each new one replaces an old one


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
