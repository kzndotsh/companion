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


# An id is made by `core/ids.py` `new_id`, never by a raw uuid elsewhere.
UUID_ALLOWED = {"core/ids.py"}


def test_ids_are_made_by_new_id() -> None:
    raw = [n for n, text in _sources().items() if "uuid.uuid4" in text and n not in UUID_ALLOWED]
    assert not raw, f"make an id with companion.core.ids.new_id, not a raw uuid: {raw}"


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


# A switch's position is a `Position` (core/switch.py), never a bare word: a typo in "shadow"
# would read as a third state. Dials and platforms keep their own words, so only on, shadow and
# off count.
MODE_WORD = re.compile(r"(?:[!=]=|\bin\b|\bnot in\b)\s*[(\[]?\s*[\"'](?:on|shadow|off)[\"']")
MODE_WORD_FIRST = re.compile(r"[\"'](?:on|shadow|off)[\"']\s*(?:[!=]=|\bin\b)")
# core/switch.py is where the words are defined and parsed; settings.py reads the daily cap, which
# takes "off" as a word of its own.
MODE_WORD_ALLOWED = {"core/switch.py", "settings.py"}


def test_no_switch_position_is_compared_as_a_bare_word() -> None:
    found = [
        f"{name}:{n}: {line.strip()}"
        for name, text in _sources().items()
        if name not in MODE_WORD_ALLOWED
        for n, line in enumerate(text.splitlines(), 1)
        if MODE_WORD.search(line) or MODE_WORD_FIRST.search(line)
    ]
    assert not found, (
        "compare with Position (`c.position(MOOD) is Position.OFF`), not a word:\n"
        + "\n".join(found)
    )
