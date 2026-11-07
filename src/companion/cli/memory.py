"""The commands on what it remembers about them: `memory` (the owner's questions, merge proposals,
the labels), `memory-pass` and `rebuild`. The questions themselves are upkeep's
(`features/upkeep/review/cli.py`)."""

from __future__ import annotations

import argparse
import asyncio

from companion import commands
from companion.features.upkeep.context import cli as context
from companion.features.upkeep.merging import cli as merging
from companion.features.upkeep.review import cli as upkeep
from companion.features.upkeep.sort import cli as worth
from companion.kit.command import Command, Group, db_args, emit, target


def _memory_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=["review", "group", "context", "label"])
    p.add_argument("--all", action="store_true", help="keep asking until none are left or you quit")
    db_args(p)


def _memory(a: argparse.Namespace) -> int:
    db, rel = target(a)
    if a.action == "group":
        return emit(asyncio.run(commands.run(db, rel, merging.group_now)))
    if a.action == "context":
        return emit(asyncio.run(commands.run(db, rel, context.write_now)))
    if a.action == "label":
        return emit(asyncio.run(commands.run(db, rel, worth.label_now)))
    return emit(upkeep.review(db, rel))


def _pass_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--from-start", action="store_true", help="re-read the whole conversation")
    db_args(p)


def _pass(a: argparse.Namespace) -> int:
    db, rel = target(a)
    return emit(asyncio.run(commands.memory_pass_now(db, rel, from_start=bool(a.from_start))))


COMMANDS = (
    Command(
        "memory",
        Group.MEMORY,
        "answer the questions about memory, or propose merges (ADR 0019)",
        _memory,
        _memory_args,
    ),
    Command(
        "rebuild",
        Group.MEMORY,
        "restate every belief under the current rules",
        lambda a: emit(asyncio.run(commands.rebuild_now(*target(a)))),
    ),
    Command("memory-pass", Group.MEMORY, "run one memory pass now", _pass, _pass_args),
)
