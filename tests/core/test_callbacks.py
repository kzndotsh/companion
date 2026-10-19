from __future__ import annotations

from companion.core.callbacks import Check, label, memories_from_card, parse, report
from companion.core.types import Json

CARD = (
    "Right now it is Sunday 13:09.\n"
    "[What you remember about them. Use it naturally, never recite it:\n"
    "- The user always wants burger. (mentioned 2 days ago)\n"
    "- The user dreads a call with their landlord. (mentioned 3 days ago; may have changed)]\n"
    "[Also known, but only touch it if they bring it up:\n"
    "- The user has asthma. (mentioned yesterday)]\n"
    "[Views of your own that you have expressed and they have approved. Hold to them:\n"
    "- The companion thinks laziness is a preference.]\n"
    "[Their message was short (3 words), so keep your reply short too.]"
)


def test_the_memories_about_them_are_read_from_a_stored_card_without_its_own_views() -> None:
    assert memories_from_card(CARD) == [
        "The user always wants burger.",
        "The user dreads a call with their landlord.",
        "The user has asthma.",
    ]


def test_a_verdict_names_the_memory_it_used_or_is_unreadable() -> None:
    labelled = label(memories_from_card(CARD))
    good: dict[str, Json] = {
        "callback": True,
        "memories": ["[m2]"],
        "accurate": True,
        "fitting": True,
        "forced": False,
    }
    check = parse(good, labelled)
    assert check is not None
    assert check.memories == ("The user dreads a call with their landlord.",)
    assert check.landed
    assert parse({**good, "memories": ["m9"]}, labelled) is None
    assert parse({**good, "callback": "yes"}, labelled) is None
    none = parse(
        {"callback": False, "memories": [], "accurate": True, "fitting": True, "forced": False},
        labelled,
    )
    assert none is not None
    assert not none.callback


def test_the_report_puts_precision_first() -> None:
    landed = Check(callback=True, memories=("a",), accurate=True, fitting=True, forced=False)
    wrong = Check(callback=True, memories=("b",), accurate=False, fitting=True, forced=False)
    forced = Check(callback=True, memories=("c",), accurate=True, fitting=True, forced=True)
    quiet = Check(callback=False, memories=(), accurate=True, fitting=True, forced=False)
    text = report([landed, wrong, forced, quiet, quiet], 7, [("how did the call go?", landed)])
    assert "5 replies checked, 3 callbacks" in text
    assert "landed 1 of 3 | wrong 1 | forced or out of place 1" in text
    assert "landed: 'how did the call go?'" in text
    assert "0 callbacks" in report([quiet], 7)
