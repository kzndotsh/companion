from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from companion import prompts
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
    public, local = tmp_path / "public", tmp_path / "local"
    public.mkdir()
    local.mkdir()
    (public / "a.json").write_text(body)
    (local / "a.json").write_text(body)
    with pytest.raises(FixtureError, match="unique"):
        load_fixtures(public, local)


def test_a_file_named_other_than_its_id_is_refused(tmp_path: Path) -> None:
    body = json.dumps(
        {
            "id": "a-local",
            "description": "d",
            "turn": "t",
            "checks": [{"kind": "max_words", "n": 1}],
        }
    )
    (tmp_path / "a.json").write_text(body)
    with pytest.raises(FixtureError, match=r"must be named a-local\.json"):
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


def test_reasoning_stays_off_unless_a_variant_asks_for_it() -> None:
    from companion.models.openrouter import OpenRouterTalker  # noqa: PLC0415

    req = _request()
    off = OpenRouterTalker("k", None, "m").body(req)  # type: ignore[arg-type]
    on = OpenRouterTalker("k", None, "m", reasoning_effort="low").body(req)  # type: ignore[arg-type]
    assert off["reasoning"] == {"enabled": False}
    assert on["reasoning"] == {"effort": "low", "exclude": True}


def test_the_length_variant_adds_the_note_for_a_short_statement_only() -> None:
    from companion.core.prompt.request import Message, TalkerRequest  # noqa: PLC0415

    short = TalkerRequest(OTHER, (Message("user", "just got home"),), card="clock")
    asked = TalkerRequest(OTHER, (Message("user", "what is for dinner?"),), card="clock")
    on = Variant("a", OTHER, length=True)
    assert "Their message was short" in request_for(short, on).card
    assert request_for(short, on).card.startswith("clock\n")
    assert request_for(asked, on).card == "clock"
    assert request_for(short, Variant("b", OTHER)).card == "clock"


def test_the_listen_variant_adds_the_fixtures_note_only_when_asked() -> None:
    from companion.core.prompt.request import Message, TalkerRequest  # noqa: PLC0415

    base = TalkerRequest(OTHER, (Message("user", "hi"),), card="clock")
    on = request_for(base, Variant("a", OTHER, listen=True), "[a note]")
    assert on.card == "clock\n[a note]"
    assert request_for(base, Variant("b", OTHER), "[a note]").card == base.card
    assert request_for(base, Variant("c", OTHER, listen=True), None).card == base.card


def test_a_mood_variant_adds_its_lines_after_the_others_and_none_changes_nothing() -> None:
    base = TalkerRequest(OTHER, (Message("user", "hi"),), card="clock")
    two = request_for(base, Variant("a", OTHER, listen=True, mood=("cozy", "playful")), "[a note]")
    lines = two.card.split("\n")
    assert lines[:2] == ["clock", "[a note]"]
    assert lines[2:] == [
        prompts.get("notes/mood-cozy").text,
        prompts.get("notes/mood-playful").text,
    ]
    assert request_for(base, Variant("b", OTHER)) == base


@pytest.mark.parametrize("bad", ["v31.md+mood-sleepy", "v31.md+mood-cozy.cozy", "v31.md+mood-"])
def test_an_unknown_or_repeated_mood_is_refused(bad: str) -> None:
    with pytest.raises(ValueError, match="bad variant"):
        parse_spec(bad)


def test_a_script_can_carry_the_labels_the_judge_would_give() -> None:
    from companion.evals.fixtures import parse_fixture  # noqa: PLC0415

    raw: Json = {
        "id": "x",
        "description": "d",
        "script": {
            "history": [],
            "user": "hi",
            "labels": {"severity": 2, "stance": "listening", "vague": False, "medical": True},
        },
        "checks": [{"kind": "max_words", "n": 10}],
    }
    fixture = parse_fixture(raw)
    assert fixture.script is not None
    assert fixture.script.labels == (2, "listening", False, True, False)


def test_a_recorded_turn_can_carry_labels_too() -> None:
    from companion.evals.fixtures import parse_fixture  # noqa: PLC0415

    raw: Json = {
        "id": "x",
        "description": "d",
        "turn": "abc123",
        "labels": {"severity": 0, "stance": "listening", "vague": False},
        "checks": [{"kind": "max_words", "n": 10}],
    }
    assert parse_fixture(raw).labels == (0, "listening", False, False, False)


@pytest.mark.parametrize(
    ("scores", "verdict"),
    [
        ({"reaction": 2, "interpretation": 0, "exploration": 0, "support": 0}, "fail"),
        ({"reaction": 2, "interpretation": 1, "exploration": 0, "support": 0}, "fail"),
        ({"reaction": 2, "interpretation": 2, "exploration": 0, "support": 0}, "pass"),
        ({"reaction": 2, "interpretation": 0, "exploration": 1, "support": 0}, "pass"),
        ({"reaction": 1, "interpretation": 0, "exploration": 0, "support": 2}, "pass"),
        ({"reaction": 0, "interpretation": 2, "exploration": 2, "support": 2}, "fail"),
        ({"reaction": 3, "interpretation": 0, "exploration": 0, "support": 0}, "unclear"),
        ({"reaction": True, "interpretation": 0, "exploration": 0, "support": 0}, "unclear"),
        ({"reaction": 1, "interpretation": 0, "exploration": 0}, "unclear"),
    ],
)
def test_an_empathy_reply_needs_a_reaction_and_something_beyond_their_words(
    scores: Json, verdict: str
) -> None:
    from companion.evals.judge import empathy_verdict  # noqa: PLC0415

    assert empathy_verdict(scores) == verdict
    assert empathy_verdict(None) == "unclear"


def test_the_epitome_check_parses_and_the_judge_hash_covers_it() -> None:
    from companion.evals.fixtures import EmpathyCheck, parse_fixture  # noqa: PLC0415

    raw: Json = {
        "id": "x",
        "description": "d",
        "script": {"history": [], "user": "hi"},
        "checks": [{"kind": "epitome"}],
    }
    assert parse_fixture(raw).checks == (EmpathyCheck(),)


def test_a_history_variant_keeps_only_the_last_messages() -> None:
    base = _request()
    short = request_for(base, Variant("a", OTHER, history=2))
    assert short.messages == base.messages[-2:]
    assert request_for(base, Variant("b", OTHER)).messages == base.messages


@pytest.mark.parametrize(
    ("text", "persona", "card", "model", "history"),
    [
        ("v10.md", "v10.md", True, None, None),
        ("v10.md+nocard", "v10.md", False, None, None),
        ("v9.md@anthropic/claude-haiku-5.5", "v9.md", True, "anthropic/claude-haiku-5.5", None),
        ("v10.md+h10", "v10.md", True, None, 10),
        ("v10.md+nocard+h6@a/b", "v10.md", False, "a/b", 6),
        ("v10.md+low", "v10.md", True, None, None),
        ("v10.md+len", "v10.md", True, None, None),
        ("v10.md+listen", "v10.md", True, None, None),
        ("v31.md+mood-cozy.playful@a/b", "v31.md", True, "a/b", None),
    ],
)
def test_variant_specs(
    text: str, persona: str, card: bool, model: str | None, history: int | None
) -> None:
    spec = parse_spec(text)
    assert (spec.persona, spec.keep_card, spec.model, spec.history) == (
        persona,
        card,
        model,
        history,
    )
    assert spec.label == text


@pytest.mark.parametrize("bad", ["v10", "v10.md+cardless", "", "v10.md+h0", "v10.md+hx"])
def test_bad_variant_specs_are_refused(bad: str) -> None:
    with pytest.raises(ValueError, match="bad variant"):
        parse_spec(bad)


async def test_a_sample_passes_only_if_every_check_passes() -> None:
    f = _fixture(MaxWords(1), JudgeCheck("c"))
    models = Models(lambda m, e: Talker("two words"), Judge("pass"))
    res = await run_eval(_plan(f, [Variant("a", PREFIX)]), models)
    [s] = res.cells[("f1", "a")].samples
    assert s.verdicts == ("fail", "pass")
    assert s.outcome == "fail"


async def test_an_unclear_judge_is_unscored_not_a_failure() -> None:
    f = _fixture(JudgeCheck("c"))
    res = await run_eval(
        _plan(f, [Variant("a", PREFIX)]), Models(lambda m, e: Talker(), Judge("unclear"))
    )
    cell = res.cells[("f1", "a")]
    assert (cell.count("pass"), cell.count("fail"), cell.count("unclear")) == (0, 0, 1)
    table = render_table(res, [f], [Variant("a", PREFIX)])
    assert "0/0 (+1?)" in table


async def test_a_real_failure_beats_an_unclear_verdict() -> None:
    f = _fixture(MaxWords(1), JudgeCheck("c"))
    models = Models(lambda m, e: Talker("two words"), Judge("unclear"))
    res = await run_eval(_plan(f, [Variant("a", PREFIX)]), models)
    assert res.cells[("f1", "a")].samples[0].outcome == "fail"


async def test_the_spend_cap_stops_the_run_and_says_so() -> None:
    f = _fixture(MaxWords(5))
    talker = Talker(cost=0.05)
    res = await run_eval(
        _plan(f, [Variant("a", PREFIX)], samples=10, cap=0.12), Models(lambda m, e: talker, Judge())
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

    def talker_for(model: str | None, effort: str | None) -> Talker:
        return made.setdefault(model, Talker())

    variants = [Variant("a", PREFIX), Variant("b", OTHER, model="other/model")]
    await run_eval(_plan(f, variants), Models(talker_for, Judge()))
    assert made[None].seen[0].prefix is PREFIX
    assert made["other/model"].seen[0].prefix is OTHER


async def test_deterministic_only_fixtures_never_call_the_judge() -> None:
    f = _fixture(MaxWords(5))
    judge = Judge()
    await run_eval(
        _plan(f, [Variant("a", PREFIX)], samples=3), Models(lambda m, e: Talker(), judge)
    )
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
    assert last == "how are you"
    assert req.card.startswith("Right now it is Thursday 12:00.")
    assert "[What you remember" in req.card


def test_directories_that_do_not_exist_are_skipped_and_ids_must_stay_unique(
    tmp_path: Path,
) -> None:
    (tmp_path / "s.json").write_text(json.dumps(_scripted()))
    assert [f.id for f in load_fixtures(tmp_path, tmp_path / "missing")] == ["s"]
    other = tmp_path / "other"
    other.mkdir()
    (other / "s.json").write_text(json.dumps(_scripted()))
    with pytest.raises(FixtureError, match="unique"):
        load_fixtures(tmp_path, other)


async def test_a_failing_provider_costs_samples_not_the_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from companion.evals import runner as runner_module  # noqa: PLC0415

    monkeypatch.setattr(runner_module, "RETRY_WAIT_SECONDS", 0.0)

    class Down:
        async def reply(self, request: object) -> object:
            del request
            msg = "429"
            raise RuntimeError(msg)

    got = await runner_module._reply_with_retry(Down(), object())  # type: ignore[arg-type]
    assert got is None


async def test_run_refuses_when_the_balance_is_below_the_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from companion.cli import eval as eval_cli  # noqa: PLC0415
    from companion.models.credits import Credits  # noqa: PLC0415

    async def low(*_: object) -> Credits:
        return Credits(bought=15, used=14.95)

    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(eval_cli, "credits", low)

    def no_env(_: Path) -> None:
        return None

    monkeypatch.setattr(eval_cli, "load_dotenv", no_env)
    args = eval_cli.EvalArgs(
        None, (Path("evals/fixtures"),), [], ["agree-and-invent"], 1, 0.2, show=False, dry_run=False
    )
    out = await eval_cli.run(args)
    assert "OpenRouter balance $0.0500" in out
    assert "top up or lower --cap" in out
    dry = await eval_cli.run(dataclasses.replace(args, dry_run=True))
    assert "balance" in dry
    assert "top up" not in dry


def test_card_and_history_switches_parse_and_label() -> None:
    spec = parse_spec("v40.md+card30+hist100")
    assert (spec.card, spec.long_history) == (30, 100)
    assert spec.label == "v40.md+card30+hist100"
    assert parse_spec("v40.md+cardall").label == "v40.md+cardall"
    with pytest.raises(ValueError, match="cardN"):
        parse_spec("v40.md+card0")


def test_the_memory_blocks_are_swapped_in_place_and_the_rest_kept() -> None:
    from companion.evals.rebuild import swap_memory  # noqa: PLC0415

    card = (
        "Right now it is Monday 10:00.\n[How they want to be referred to: she/her]\n"
        "[What you remember about them. Use it naturally, never recite it:\n- old]\n"
        "[Older, and may be out of date. Do not assume these still hold:\n- older]\n"
        "[A note that stays.]"
    )
    new = swap_memory(
        card, "[What you remember about them. Use it naturally, never recite it:\n- new]"
    )
    assert "- old" not in new
    assert "- older" not in new
    assert new.index("referred to") < new.index("- new") < new.index("A note that stays")
