from __future__ import annotations

from companion.core.turn.address import address_note


def test_the_pinned_line_says_how_to_refer_to_them_and_nothing_when_unset() -> None:
    note = address_note("  she/her, a woman; use feminine words  ")
    assert note == (
        "[How they want to be referred to: she/her, a woman; use feminine words."
        " Get it right whenever you refer to them, without bringing it up, and do not turn it into"
        " a pet name or a word you keep calling them.]"
    )
    assert address_note("") is None
    assert address_note(None) is None
