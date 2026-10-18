"""`companion eval`: replay recorded turns against variants and print one table."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import httpx

from companion import characters, prompts
from companion.core.clock import utc_now
from companion.core.listening import Judgement as ListenJudgement
from companion.core.listening import listening_note
from companion.core.prompt.prefix import Prefix, build_prefix
from companion.core.prompt.request import Message, TalkerRequest
from companion.core.replay import ReplayError
from companion.core.talker import Talker
from companion.daemon import load_dotenv
from companion.evals import judge as judge_module
from companion.evals.fixtures import (
    EmpathyCheck,
    Fixture,
    FixtureError,
    JudgeCheck,
    Script,
    load_fixtures,
)
from companion.evals.report import render_replies, render_table, save
from companion.evals.runner import Models, Plan, Variant, run_eval
from companion.evals.variants import parse_spec
from companion.models.openrouter import DEFAULT_MODEL, OpenRouterExtractor, OpenRouterTalker
from companion.store.sqlite.replay import replay_file

JUDGE_MODEL = "anthropic/claude-haiku-5.5"
EST_TALKER = 0.0036
EST_JUDGE = 0.0004


def _variants(specs: list[str]) -> list[Variant]:
    out: list[Variant] = []
    for text in specs:
        spec = parse_spec(text)
        try:
            persona = prompts.get("system/persona", spec.persona.removesuffix(".md"))
        except KeyError as err:
            msg = f"no persona file {spec.persona}"
            raise ValueError(msg) from err
        try:
            character = characters.load(spec.character) if spec.character else None
        except characters.CharacterError as err:
            raise ValueError(str(err)) from err
        prefix = build_prefix(characters.system_prompt(persona.raw, character))
        out.append(
            Variant(
                spec.label,
                prefix,
                spec.keep_card,
                spec.model,
                spec.history,
                spec.effort,
                spec.length,
                spec.listen,
            )
        )
    return out


def describe(fixtures: list[Fixture]) -> str:
    lines = [
        f"{f.id:34} {'script' if f.script else 'local turn':10} {len(f.checks)} checks"
        f"  {f.description}"
        for f in fixtures
    ]
    return "\n".join(lines) + "\n"


def script_request(script: Script, prefix: Prefix) -> TalkerRequest:
    """Build the request a fixture script describes, shaped like a real one: the user's words, and
    a system block with the clock line and an optional memory block."""
    messages = [
        Message("user" if role == "user" else "assistant", text) for role, text in script.history
    ]
    messages.append(Message("user", script.user))
    clock = script.clock or "Right now it is Thursday 12:00."
    card = "\n".join(part for part in (clock, script.memory) if part)
    return TalkerRequest(prefix=prefix, messages=tuple(messages), card=card)


def _listening_notes(fixtures: list[Fixture]) -> dict[str, str]:
    """The note each fixture's labels would produce, for the `+listen` variant."""
    out: dict[str, str] = {}
    for f in fixtures:
        labels = f.labels or (f.script.labels if f.script is not None else None)
        if labels is not None:
            severity, stance, vague, medical = labels
            replies = (
                [text for role, text in f.script.history if role == "assistant"] if f.script else []
            )
            note = listening_note(ListenJudgement(severity, stance, vague, medical), replies)
            if note is not None:
                out[f.id] = note
    return out


def estimate(fixtures: list[Fixture], variants: int, samples: int) -> float:
    calls = variants * samples
    return sum(
        calls
        * (EST_TALKER + EST_JUDGE * sum(isinstance(c, JudgeCheck | EmpathyCheck) for c in f.checks))
        for f in fixtures
    )


@dataclass(frozen=True, slots=True)
class EvalArgs:
    db: Path | None
    fixtures_dirs: tuple[Path, ...]
    specs: list[str]
    only: list[str]
    samples: int
    cap: float
    show: bool
    dry_run: bool


async def run(a: EvalArgs) -> str:
    db, samples, cap = a.db, a.samples, a.cap
    load_dotenv(Path(".env"))
    fixtures = load_fixtures(*a.fixtures_dirs)
    if a.only:
        fixtures = [f for f in fixtures if f.id in a.only]
    if not fixtures:
        return "no fixtures to run\n"
    variants = _variants(a.specs)
    plan_cost = estimate(fixtures, len(variants), samples)
    header = (
        f"{len(fixtures)} fixtures x {len(variants)} variants x {samples} samples"
        f" = {len(fixtures) * len(variants) * samples} replies, about ${plan_cost:.3f}"
        f" (cap ${cap:.2f})\n"
    )
    if a.dry_run:
        return header
    requests: dict[str, TalkerRequest] = {}
    for f in fixtures:
        if f.script is not None:
            requests[f.id] = script_request(f.script, variants[0].prefix)
        elif db is None or f.turn is None:
            return f"fixture {f.id} replays a recorded turn and needs a local database (--db)\n"
        else:
            try:
                requests[f.id] = replay_file(db, f.turn).request
            except ReplayError as err:
                return f"fixture {f.id}: {err}\n"
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return "OPENROUTER_API_KEY is not set (put it in .env)\n"
    async with httpx.AsyncClient() as client:

        def talker_for(model: str | None, effort: str | None) -> Talker:
            return OpenRouterTalker(
                key,
                client,
                model or DEFAULT_MODEL,
                max_tokens=400 if effort is None else 4000,
                reasoning_effort=effort,
            )

        models = Models(talker_for, OpenRouterExtractor(key, client, JUDGE_MODEL))
        listening = _listening_notes(fixtures)
        plan = Plan(fixtures, requests, variants, samples, cap, listening)
        results = await run_eval(plan, models)
    stamp = utc_now().strftime("%Y%m%d-%H%M%S")
    path = Path("evals/results") / f"{stamp}.json"
    save(path, results, fixtures, variants, judge_module.judge_hash())
    body = render_table(results, fixtures, variants)
    if a.show:
        body += "\n" + render_replies(results, fixtures, variants)
    return f"{header}\n{body}\n\nsaved {path}\n"


__all__ = ["FixtureError", "describe", "estimate", "run"]
