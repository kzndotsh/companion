from __future__ import annotations

import json
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import Message, TalkerRequest
from companion.core.talker import Reply
from companion.core.types import Json
from companion.evals.checks import run_deterministic
from companion.evals.fixtures import (
    Fixture,
    FixtureError,
    JudgeCheck,
    MaxWords,
    Regex,
    load_fixtures,
    parse_fixture,
)
from companion.evals.judge import judge_hash, parse
from companion.evals.report import render_table
from companion.evals.runner import Models, Plan, Variant, request_for, run_eval, strip_card
from companion.evals.variants import parse_spec

PREFIX = build_prefix("You are steady and warm. " * 200)
OTHER = build_prefix("You are blunt and brief. " * 200)
CARD = (
    "[Thursday 12:00]\n[What you remember about them. Use it naturally, never recite it:\n"
    "- The user likes climbing. (told you Thu Oct 15)]\n"
    "[Also known, but only touch it if they bring it up:\n- The user has a secret.]\n\nhello"
)


def _fixture(*checks: object) -> Fixture:
    return Fixture("f1", "a test fixture", tuple(checks), turn="t1")  # type: ignore[arg-type]


class Talker:
    def __init__(self, text: str = "nice", cost: float = 0.01) -> None:
        self.text, self.cost = text, cost
        self.seen: list[TalkerRequest] = []

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        return Reply(self.text, "m", 5, cost_usd=self.cost)


class Judge:
    def __init__(self, verdict: str = "pass", cost: float = 0.001) -> None:
        self.verdict, self.cost, self.calls = verdict, cost, 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        self.calls += 1
        return Extraction({"verdict": self.verdict, "confidence": 0.9}, "j", self.cost, 1)


def _request() -> TalkerRequest:
    return TalkerRequest(PREFIX, (Message("user", "earlier"), Message("user", CARD)))


def _plan(f: Fixture, variants: list[Variant], samples: int = 1, cap: float = 1.0) -> Plan:
    return Plan([f], {"f1": _request()}, variants, samples, cap)


def test_max_words_and_regex_checks() -> None:
    assert run_deterministic(MaxWords(3), "one two three") == "pass"
    assert run_deterministic(MaxWords(3), "one two three four") == "fail"
    assert run_deterministic(Regex(r"^they really are"), "They really are.") == "fail"
    assert run_deterministic(Regex(r"^they really are"), "i dont know") == "pass"
    assert run_deterministic(Regex(r"thanks", must_match=True), "no") == "fail"


def test_a_fixture_must_be_well_formed() -> None:
    good: Json = {
        "id": "a",
        "description": "d",
        "turn": "t",
        "checks": [{"kind": "max_words", "n": 5}, {"kind": "judge", "criterion": "c"}],
    }
    assert len(parse_fixture(good).checks) == 2
    bads: list[Json] = [
        {"id": "a", "description": "d", "turn": "t", "checks": []},
        {"id": "a", "description": "d", "turn": "t", "checks": [{"kind": "nope"}]},
        {"id": "a", "description": "d", "turn": "t", "checks": [{"kind": "regex", "pattern": "("}]},
        {"id": "", "description": "d", "turn": "t", "checks": [{"kind": "max_words", "n": 1}]},
    ]
    for bad in bads:
        with pytest.raises(FixtureError):
            parse_fixture(bad)


def test_duplicate_ids_are_refused(tmp_path: Path) -> None:
    body = json.dumps(
        {"id": "a", "description": "d", "turn": "t", "checks": [{"kind": "max_words", "n": 1}]}
    )
    (tmp_path / "1.json").write_text(body)
    (tmp_path / "2.json").write_text(body)
    with pytest.raises(FixtureError, match="unique"):
        load_fixtures(tmp_path)


def test_the_judge_is_hashed_and_off_menu_answers_are_rejected() -> None:
    assert len(judge_hash()) == 12
    assert parse({"verdict": "pass", "confidence": 0.9}) == ("pass", 0.9)
    assert parse({"verdict": "maybe", "confidence": 0.9}) is None
    assert parse({"verdict": "pass", "confidence": True}) is None


def test_strip_card_keeps_the_clock_and_what_they_typed() -> None:
    out = strip_card(CARD)
    assert "[Thursday 12:00]" in out
    assert out.endswith("hello")
    assert "remember" not in out
    assert "secret" not in out


def test_a_variant_swaps_only_the_prefix_and_optionally_the_card() -> None:
    base = _request()
    with_card = request_for(base, Variant("a", OTHER))
    no_card = request_for(base, Variant("b", OTHER, keep_card=False))
    assert with_card.prefix is OTHER
    assert with_card.messages == base.messages
    assert "remember" not in no_card.messages[-1].content
    assert no_card.messages[0] == base.messages[0]


@pytest.mark.parametrize(
    ("text", "persona", "card", "model"),
    [
        ("v10.md", "v10.md", True, None),
        ("v10.md+nocard", "v10.md", False, None),
        ("v9.md@anthropic/claude-haiku-5.5", "v9.md", True, "anthropic/claude-haiku-5.5"),
    ],
)
def test_variant_specs(text: str, persona: str, card: bool, model: str | None) -> None:
    spec = parse_spec(text)
    assert (spec.persona, spec.keep_card, spec.model) == (persona, card, model)
    assert spec.label == text


@pytest.mark.parametrize("bad", ["v10", "v10.md+cardless", ""])
def test_bad_variant_specs_are_refused(bad: str) -> None:
    with pytest.raises(ValueError, match="bad variant"):
        parse_spec(bad)


async def test_a_sample_passes_only_if_every_check_passes() -> None:
    f = _fixture(MaxWords(1), JudgeCheck("c"))
    models = Models(lambda m: Talker("two words"), Judge("pass"))
    res = await run_eval(_plan(f, [Variant("a", PREFIX)]), models)
    [s] = res.cells[("f1", "a")].samples
    assert s.verdicts == ("fail", "pass")
    assert s.outcome == "fail"


async def test_an_unclear_judge_is_unscored_not_a_failure() -> None:
    f = _fixture(JudgeCheck("c"))
    res = await run_eval(
        _plan(f, [Variant("a", PREFIX)]), Models(lambda m: Talker(), Judge("unclear"))
    )
    cell = res.cells[("f1", "a")]
    assert (cell.count("pass"), cell.count("fail"), cell.count("unclear")) == (0, 0, 1)
    table = render_table(res, [f], [Variant("a", PREFIX)])
    assert "0/0 (+1?)" in table


async def test_a_real_failure_beats_an_unclear_verdict() -> None:
    f = _fixture(MaxWords(1), JudgeCheck("c"))
    models = Models(lambda m: Talker("two words"), Judge("unclear"))
    res = await run_eval(_plan(f, [Variant("a", PREFIX)]), models)
    assert res.cells[("f1", "a")].samples[0].outcome == "fail"


async def test_the_spend_cap_stops_the_run_and_says_so() -> None:
    f = _fixture(MaxWords(5))
    talker = Talker(cost=0.05)
    res = await run_eval(
        _plan(f, [Variant("a", PREFIX)], samples=10, cap=0.12), Models(lambda m: talker, Judge())
    )
    cell = res.cells[("f1", "a")]
    assert res.stopped_by_cap
    assert cell.skipped > 0
    assert len(cell.samples) + cell.skipped == 10
    assert res.spent < 0.12 + 0.05 * 4  # bounded by the concurrency window
    assert "STOPPED EARLY" in render_table(res, [f], [Variant("a", PREFIX)])


async def test_each_variant_uses_its_own_prefix_and_model() -> None:
    f = _fixture(MaxWords(5))
    made: dict[str | None, Talker] = {}

    def talker_for(model: str | None) -> Talker:
        return made.setdefault(model, Talker())

    variants = [Variant("a", PREFIX), Variant("b", OTHER, model="other/model")]
    await run_eval(_plan(f, variants), Models(talker_for, Judge()))
    assert made[None].seen[0].prefix is PREFIX
    assert made["other/model"].seen[0].prefix is OTHER


async def test_deterministic_only_fixtures_never_call_the_judge() -> None:
    f = _fixture(MaxWords(5))
    judge = Judge()
    await run_eval(_plan(f, [Variant("a", PREFIX)], samples=3), Models(lambda m: Talker(), judge))
    assert judge.calls == 0


def _scripted() -> dict[str, Json]:
    return {
        "id": "s",
        "description": "d",
        "script": {
            "history": [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "hey"}],
            "user": "how are you",
            "memory": "[What you remember about them:\n- The user likes tea.]",
        },
        "checks": [{"kind": "max_words", "n": 5}],
    }


def test_a_scripted_fixture_needs_no_turn() -> None:
    f = parse_fixture(_scripted())
    assert f.turn is None
    assert f.script is not None
    assert f.script.history == (("user", "hi"), ("assistant", "hey"))
    assert f.script.user == "how are you"


def test_a_fixture_needs_exactly_one_of_turn_and_script() -> None:
    both = _scripted()
    both["turn"] = "abc"
    neither = _scripted()
    del neither["script"]
    for bad in (both, neither):
        with pytest.raises(FixtureError, match="exactly one"):
            parse_fixture(bad)


@pytest.mark.parametrize(
    "script",
    [
        {"user": "x", "history": [{"role": "robot", "text": "beep"}]},
        {"user": "x", "history": "not a list"},
        {"history": []},
        {"user": "x", "memory": 3},
    ],
)
def test_a_malformed_script_is_refused(script: Json) -> None:
    raw = _scripted()
    raw["script"] = script
    with pytest.raises(FixtureError):
        parse_fixture(raw)


def test_a_script_becomes_a_request_shaped_like_a_real_one() -> None:
    from companion.cli.eval import script_request  # noqa: PLC0415

    f = parse_fixture(_scripted())
    assert f.script is not None
    req = script_request(f.script, PREFIX)
    assert req.prefix is PREFIX
    assert [m.role for m in req.messages] == ["user", "assistant", "user"]
    last = req.messages[-1].content
    assert last.startswith("[Thursday 12:00]\n[What you remember")
    assert last.endswith("\nhow are you")


def test_directories_that_do_not_exist_are_skipped_and_ids_must_stay_unique(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.json").write_text(json.dumps(_scripted()))
    assert [f.id for f in load_fixtures(tmp_path, tmp_path / "missing")] == ["s"]
    other = tmp_path / "other"
    other.mkdir()
    (other / "dup.json").write_text(json.dumps(_scripted()))
    with pytest.raises(FixtureError, match="unique"):
        load_fixtures(tmp_path, other)
