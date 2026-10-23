from __future__ import annotations

from companion.core.turn.ownup import NOTE, WINDOW, owned, owned_note


def test_an_own_up_is_read_and_sympathy_is_not() -> None:
    for reply in (
        "yeah, I got that wrong 😭 he's the main character",
        "ohh, got it. sorry, I tangled the timeline.",
        "right, my bad. what's next?",
        "I should\u2019ve remembered that one.",
        "okay, okay 😭 I deserved that one",
    ):
        assert owned(reply), reply
    for reply in (
        "oh, honey. i'm sorry she hurt you.",
        "I'm sorry it's hitting you again.",
        "you never have to apologize for vanishing",
        "right, the show is based on the books",
    ):
        assert not owned(reply), reply


def test_the_note_follows_a_recent_own_up_only() -> None:
    ok, slip = "nice, enjoy it", "my bad, I mixed it up"
    assert owned_note([ok, slip], repairing=False) == NOTE.text
    assert owned_note([slip, *[ok] * WINDOW], repairing=False) is None  # long enough ago
    assert owned_note([ok, ok], repairing=False) is None


def test_when_they_say_it_got_them_wrong_the_repair_note_answers_instead() -> None:
    assert owned_note(["my bad, I mixed it up"], repairing=True) is None
