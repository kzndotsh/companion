from __future__ import annotations

import pytest

from companion.core.listening import (
    Judgement,
    listening_note,
    offered_recently,
    parse,
    render_reason,
)
from companion.core.types import Json


def _j(
    severity: int = 1, stance: str = "listening", *, vague: bool = False, medical: bool = False
) -> Judgement:
    return Judgement(severity, stance, vague, medical)


def test_a_trivial_vent_gets_plain_sympathy_and_no_advice_or_cause_question() -> None:
    note = listening_note(_j(0))
    assert note is not None
    assert "No advice" in note
    assert "do not ask what caused it" in note
    assert "No joke, pun, running gag" in note
    assert "do not retell what they said" in note


def test_everyday_friction_may_get_a_fact_a_nudge_or_one_question() -> None:
    note = listening_note(_j(1))
    assert note is not None
    assert "gentle suggestion" in note
    assert "single question" in note
    assert "repeats none of their details" in note
    assert "talk about it" not in note  # they said what it is, so no offer


def test_vague_distress_gets_the_offer_to_talk_once() -> None:
    assert "whether they want to talk about it" in str(listening_note(_j(1, vague=True)))
    after_an_offer = ["damn, im sorry. wanna talk about it or?"]
    assert "talk about it" not in str(listening_note(_j(1, vague=True), after_an_offer))


def test_serious_things_get_the_weight_named_no_advice_and_an_offer() -> None:
    note = listening_note(_j(2))
    assert note is not None
    assert "Do not advise on what to do or on treatment" in note
    assert "mention once that someone qualified" in note
    assert "everyday words" in note
    assert "under about 35 words" in note
    assert "talk about it" in note
    assert "talk about it" not in str(listening_note(_j(2), ["do you want to talk about it?"]))


@pytest.mark.parametrize(
    "judged",
    [_j(3), _j(1, "inviting"), _j(2, "other"), _j(0, "other")],
)
def test_acute_things_and_other_stances_get_no_note(judged: Judgement) -> None:
    assert listening_note(judged) is None


def test_a_serious_health_topic_always_points_to_a_doctor_or_prescriber_once() -> None:
    plain = str(listening_note(_j(2)))
    health = str(listening_note(_j(2, medical=True)))
    assert "a doctor can help" in health
    assert "a doctor can help" not in plain
    assert "say once" in health
    assert "already seeing a doctor" in health


def test_the_note_is_one_bracketed_line() -> None:
    for severity in (0, 1, 2):
        note = str(listening_note(_j(severity, vague=True)))
        assert note.startswith("[")
        assert note.endswith("]")
        assert "\n" not in note
        assert "]" not in note[:-1]


def test_only_the_last_few_replies_count_as_having_offered() -> None:
    old = ["want to talk about it?"] + ["ok"] * 4
    assert not offered_recently(old)
    assert offered_recently(["ok", "wanna talk?", "ok"])
    assert offered_recently(["Do you want to talk it through?"])


def test_parse_accepts_labels_and_refuses_anything_off_the_menu() -> None:
    ok: Json = {"severity": 2, "stance": "listening", "vague": False, "medical": False}
    assert parse(ok) == _j(2)
    bad_answers: list[Json] = [
        None,
        {},
        {"severity": 4, "stance": "listening", "vague": False, "medical": False},
        {"severity": True, "stance": "listening", "vague": False, "medical": False},
        {"severity": 1, "stance": "venting", "vague": False, "medical": False},
        {"severity": 1, "stance": "listening", "vague": "no", "medical": False},
        {"severity": 1, "stance": "listening", "vague": False},
    ]
    for bad in bad_answers:
        assert parse(bad) is None


def test_the_logged_reason_names_the_labels_and_the_missing_crisis_path() -> None:
    assert "severity 2, listening" in render_reason(_j(2), "x")
    assert "listening note added" in render_reason(_j(1, vague=True), "x")
    assert "no crisis path" in render_reason(_j(3), None)
    assert render_reason(_j(1, "inviting"), None) == "no listening note: severity 1, inviting"
