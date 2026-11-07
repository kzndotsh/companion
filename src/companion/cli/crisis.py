"""`companion crisis --check --cap D`: the risk judge on the public fixtures (ADR 0022), on the
models the bot reads it with (`COMPANION_JUDGE_ROUTES`). It costs money, so it needs a cap, shows
the OpenRouter balance first and refuses when the balance is below the cap. The check
itself is `features/crisis/cli.py`."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

from companion.compose import api_key, extractor
from companion.features.crisis.cli import FIXTURES, check, load_cases
from companion.features.crisis.cli import run as counts
from companion.kit.command import Command, Group, db_args, emit, target
from companion.lib.vote import READS
from companion.models.credits import spend_gate
from companion.settings import Settings

EST_READ = 0.0006  # dollars per risk read, a guess for the plan line only


async def run(path: Path, cap: float) -> str:
    s = Settings.from_env()
    cases = load_cases(path)
    header = (
        f"{len(cases)} cases x {READS} reads, at most about ${len(cases) * READS * EST_READ:.3f}"
        f" (cap ${cap:.2f})\n"
    )
    key = api_key("OPENROUTER_API_KEY")
    if not key:
        return "OPENROUTER_API_KEY is not set (put it in .env)\n"
    async with httpx.AsyncClient() as client:
        gate = await spend_gate(key, client, cap)
        header += gate.line
        if gate.refusal:
            return header + gate.refusal
        return header + await check(cases, extractor(client, s, s.judge_routes), cap)


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--check", action="store_true", help="read every crisis fixture three times (model calls)"
    )
    p.add_argument("--cap", type=float, help="required with --check: stop at this much spend")
    p.add_argument("--fixtures", type=Path, default=FIXTURES, help="the fixture file")
    db_args(p)


def _run(a: argparse.Namespace) -> int:
    if not a.check:
        return emit(counts(*target(a)))
    if a.cap is None or a.cap <= 0:
        sys.stderr.write("pass --cap with --check, for example --cap 0.10; it costs money\n")
        return 2
    return emit(asyncio.run(run(Path(a.fixtures), float(a.cap))))


COMMANDS = (
    Command(
        "crisis",
        Group.MEASURING,
        "how often each crisis level was read lately, or --check the fixtures",
        _run,
        _args,
    ),
)
