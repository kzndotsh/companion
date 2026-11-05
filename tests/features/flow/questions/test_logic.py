from __future__ import annotations

from companion.features.flow.questions.logic import RUN, RUN_NOTE, asked, question_note


def test_a_reply_that_asks_is_read() -> None:
    assert asked("ooh which one did you pick?")
    assert not asked("that sounds so cozy, enjoy it")


def test_the_note_follows_only_a_full_run_of_questions() -> None:
    q, plain = "how did it go?", "nice, enjoy it"
    assert question_note([q] * RUN) == RUN_NOTE.text
    assert question_note([plain, *[q] * RUN]) == RUN_NOTE.text
    assert question_note([*[q] * RUN, plain]) is None  # the run is already broken
    assert question_note([q] * (RUN - 1)) is None  # too short to be a run
    assert question_note([q, plain, q]) is None
