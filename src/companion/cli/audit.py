"""`companion audit`: judge recent replies within a spend cap, then report."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from companion import commands
from companion.features.audits.callbacks import cli as callbacks
from companion.features.audits.invented import cli as invented
from companion.kit.command import Command, Group, db_args, emit, target


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "which",
        choices=("callbacks", "invented"),
        help="callbacks to memories, or made-up facts about them (G42)",
    )
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--cap", type=float, default=0.10, help="stop judging at this much spend")
    p.add_argument(
        "--dump", type=Path, help="invented: write the candidates with their context, to confirm"
    )
    db_args(p)


def _run(a: argparse.Namespace) -> int:
    db, rel = target(a)
    days, cap = int(a.days), float(a.cap)
    if a.which == "invented":
        return emit(
            asyncio.run(commands.run(db, rel, lambda x: invented.judge_now(x, days, cap, a.dump)))
        )
    return emit(asyncio.run(commands.run(db, rel, lambda x: callbacks.judge_now(x, days, cap))))


COMMANDS = (
    Command(
        "audit",
        Group.MEASURING,
        "judge recent replies within a spend cap, then report",
        _run,
        _args,
    ),
)
