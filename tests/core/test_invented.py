from __future__ import annotations

from companion.core.invented import Statement, Support, build_prompt, invented, parse, report
from companion.core.types import Json

REPLY = "since you're always up late, grab a snack. i love rainy nights"


def test_only_quotes_from_the_reply_that_are_said_to_them_are_kept() -> None:
    data: Json = {
        "statements": [
            {"quote": "since you're always up late", "support": "none"},
            {"quote": "i love rainy nights", "support": "none"},  # about itself, not them
            {"quote": "you hate snacks", "support": "none"},  # not in the reply
            {"quote": "grab a snack", "support": "maybe"},
        ]
    }
    assert parse(data, REPLY) == [Statement("since you're always up late", Support.NONE)]
    assert parse({"oops": 1}, REPLY) is None


def test_the_report_counts_candidates_and_says_they_are_unconfirmed() -> None:
    late = Statement("since you're always up late", Support.NONE)
    told = Statement("you told me", Support.CONVERSATION)
    checks: list[tuple[str, list[Statement]]] = [
        (REPLY, [late]),
        ("you told me so", [told]),
        ("nice", []),
    ]
    assert invented([late, told]) == [late]
    out = report(checks, 2)
    assert "3 replies checked, 2 said something about them, 1 candidates" in out
    assert "unconfirmed" in out
    assert "since you're always up late" in out


def test_the_prompt_shows_the_talk_the_memory_and_the_reply() -> None:
    text = build_prompt([("user", "hey"), ("companion", "hi")], [], REPLY)
    assert "[USER] hey\n[COMPANION] hi" in text
    assert "Its memory of the user:\n(nothing)" in text
    assert text.endswith(f"The reply: {REPLY}")
