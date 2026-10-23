"""`companion eval`: replay recorded turns against variants and print one table."""

from __future__ import annotations

import difflib
import os
from dataclasses import dataclass
from pathlib import Path

import httpx

from companion import characters, prompts
from companion.core.clock import utc_now
from companion.core.prompt.prefix import Prefix, build_prefix
from companion.core.prompt.request import Message, TalkerRequest
from companion.core.replay import ReplayError
from companion.core.talker import Talker
from companion.core.turn.length import length_target
from companion.core.turn.listening import SERIOUS, listening_note, rude_note
from companion.core.turn.listening import Judgement as ListenJudgement
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
from companion.evals.rebuild import rebuilt
from companion.evals.report import render_replies, render_table, save
from companion.evals.runner import Models, Plan, Variant, run_eval
from companion.evals.variants import parse_spec
from companion.features.lore.logic import lore_note
from companion.models.credits import charged_since, credits
from companion.models.kiro import PREFIX as KIRO
from companion.models.kiro import KiroTalker, kiro_key
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
        prefix = build_prefix(
            characters.system_prompt(persona.raw, character, roleplay=spec.roleplay)
        )
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
                spec.echo,
                spec.mood,
                spec.resample,
                spec.tags,
                spec.tags_notes,
                lore=spec.lore,
                tail=character.scene_reminder if character is not None and spec.roleplay else "",
            )
        )
    return out


def _rebuilt(
    fixtures: list[Fixture], specs: list[str], db: Path | None
) -> dict[tuple[str, str], TalkerRequest] | str:
    """Requests rebuilt for +cardN and +histN variants, one per recorded turn and variant. Those
    switches need a recorded turn and its database; a scripted fixture keeps its own card."""
    out: dict[tuple[str, str], TalkerRequest] = {}
    for spec in map(parse_spec, specs):
        if spec.card is None and spec.long_history is None:
            continue
        for f in fixtures:
            if f.turn is None:
                continue
            if db is None:
                return "+card and +hist rebuild recorded turns and need a database (--db)\n"
            out[(f.id, spec.label)] = rebuilt(
                db, f.turn, card_size=spec.card, history=spec.long_history
            )
    return out


def _inputs(
    fixtures: list[Fixture], specs: list[str], db: Path | None, prefix: Prefix
) -> tuple[dict[str, TalkerRequest], dict[tuple[str, str], TalkerRequest]] | str:
    requests = _requests(fixtures, db, prefix)
    if isinstance(requests, str):
        return requests
    again = _rebuilt(fixtures, specs, db)
    return again if isinstance(again, str) else (requests, again)


def _select(fixtures: list[Fixture], only: list[str]) -> list[Fixture] | str:
    """The fixtures named with --fixture, or why one name matches none (with the closest id)."""
    if not only:
        return fixtures
    known = {f.id for f in fixtures}
    if unknown := [x for x in only if x not in known]:
        hints = {x: difflib.get_close_matches(x, known, n=1) for x in unknown}
        listed = ", ".join(f"{x} (did you mean {h[0]}?)" if h else x for x, h in hints.items())
        return f"no fixture with the id {listed}\n"
    return [f for f in fixtures if f.id in only]


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
    """The notes each fixture's labels would produce, for the `+listen` variant: the length line a
    serious message gets, then the listening note, as the bot sends them."""
    out: dict[str, str] = {}
    for f in fixtures:
        labels = f.labels or (f.script.labels if f.script is not None else None)
        if labels is not None:
            severity, stance, vague, medical, rude = labels
            replies = (
                [text for role, text in f.script.history if role == "assistant"] if f.script else []
            )
            judged = ListenJudgement(severity, stance, vague, medical, rude)
            note = listening_note(judged, replies, seed=f.id)
            size = length_target("", severity=severity) if severity >= SERIOUS else None
            notes = [
                n for n in (size.note if size else None, note, rude_note(judged)) if n is not None
            ]
            if notes:
                out[f.id] = "\n".join(notes)
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


def _requests(
    fixtures: list[Fixture], db: Path | None, prefix: Prefix
) -> dict[str, TalkerRequest] | str:
    """Each fixture's request, or why one cannot be built."""
    out: dict[str, TalkerRequest] = {}
    for f in fixtures:
        if f.script is not None:
            out[f.id] = script_request(f.script, prefix)
        elif db is None or f.turn is None:
            return f"fixture {f.id} replays a recorded turn and needs a local database (--db)\n"
        else:
            try:
                out[f.id] = replay_file(db, f.turn).request
            except ReplayError as err:
                return f"fixture {f.id}: {err}\n"
    return out


async def run(a: EvalArgs) -> str:
    db, samples, cap = a.db, a.samples, a.cap
    load_dotenv(Path(".env"))
    fixtures = _select(load_fixtures(*a.fixtures_dirs), a.only) or "no fixtures to run\n"
    if isinstance(fixtures, str):
        return fixtures
    variants = _variants(a.specs)
    plan_cost = estimate(fixtures, len(variants), samples)
    header = (
        f"{len(fixtures)} fixtures x {len(variants)} variants x {samples} samples"
        f" = {len(fixtures) * len(variants) * samples} replies, at most about ${plan_cost:.3f}"
        f" (cap ${cap:.2f})\n"
    )
    key = os.environ.get("OPENROUTER_API_KEY")
    async with httpx.AsyncClient() as client:
        before = await credits(key, client) if key else None
        if before is not None:
            header += f"OpenRouter balance ${before.balance:.4f}\n"
        if a.dry_run:
            return header
        if not key:
            return "OPENROUTER_API_KEY is not set (put it in .env)\n"
        if before is not None and before.balance < cap:
            return (
                header
                + "the balance is below the cap and the bot shares it: top up or lower --cap\n"
            )
        built = _inputs(fixtures, a.specs, db, variants[0].prefix)
        if isinstance(built, str):
            return built
        requests, rebuilt_requests = built

        def talker_for(model: str | None, effort: str | None) -> Talker:
            if model is not None and model.startswith(KIRO):
                return KiroTalker(kiro_key(), client, model.removeprefix(KIRO))
            return OpenRouterTalker(
                key,
                client,
                model or DEFAULT_MODEL,
                max_tokens=400 if effort is None else 4000,
                reasoning_effort=effort,
            )

        models = Models(talker_for, OpenRouterExtractor(key, client, JUDGE_MODEL))
        listening = _listening_notes(fixtures)
        lore = {
            f.id: note
            for f in fixtures
            if f.script is not None and (note := lore_note(f.script.lore))
        }
        plan = Plan(
            fixtures, requests, variants, samples, cap, listening, rebuilt_requests, lore=lore
        )
        results = await run_eval(plan, models)
        if before is not None:
            results.charged = await charged_since(key, client, before, results.spent)
    stamp = utc_now().strftime("%Y%m%d-%H%M%S")
    path = Path("evals/results") / f"{stamp}.json"
    save(path, results, fixtures, variants, judge_module.judge_hash())
    body = render_table(results, fixtures, variants)
    if a.show:
        body += "\n" + render_replies(results, fixtures, variants)
    return f"{header}\n{body}\n\nsaved {path}\n"


__all__ = ["FixtureError", "describe", "estimate", "run"]
