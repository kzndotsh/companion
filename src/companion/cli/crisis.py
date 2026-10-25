"""`companion crisis --check --cap D`: the risk judge on the public fixtures (ADR 0022), with the
bot's own judges' model. It costs money, so it needs a cap, shows the OpenRouter balance first and
refuses when the balance is below the cap. The check itself is `features/crisis/cli.py`."""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from companion.daemon import extractor, load_dotenv
from companion.features.crisis.cli import check, load_cases
from companion.lib.vote import READS
from companion.models.credits import credits

EST_READ = 0.0006  # dollars per risk read, a guess for the plan line only


async def run(path: Path, cap: float) -> str:
    load_dotenv(Path(".env"))
    cases = load_cases(path)
    header = (
        f"{len(cases)} cases x {READS} reads, at most about ${len(cases) * READS * EST_READ:.3f}"
        f" (cap ${cap:.2f})\n"
    )
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return "OPENROUTER_API_KEY is not set (put it in .env)\n"
    async with httpx.AsyncClient() as client:
        before = await credits(key, client)
        if before is not None:
            header += f"OpenRouter balance ${before.balance:.4f}\n"
            if before.balance < cap:
                return header + "the balance is below the cap: top up or lower --cap\n"
        return header + await check(cases, extractor(client), cap)
