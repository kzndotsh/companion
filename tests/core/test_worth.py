from __future__ import annotations

from companion.core.worth import ASK_ABOUT_THE_BOT, ASK_ROUTINE, to_ask, verdict


def test_code_acts_only_when_every_read_agrees() -> None:
    assert verdict(["about_the_bot"] * 3) == "about_the_bot"
    assert verdict(["routine"] * 3) == "routine"
    assert verdict(["keep"] * 3) == "keep"


def test_any_doubt_becomes_a_question_and_failed_reads_change_nothing() -> None:
    assert verdict(["about_the_bot", "keep", "keep"]) == "unsure"
    assert verdict(["unsure"] * 3) == "unsure"
    assert verdict([None, None, None]) == "keep"
    assert verdict(["keep", "keep", None]) == "keep"


def test_a_memory_kept_before_the_rule_is_asked_about_instead() -> None:
    assert to_ask("about_the_bot") == ASK_ABOUT_THE_BOT
    assert to_ask("routine") == ASK_ROUTINE
    assert to_ask("keep") == "keep"
