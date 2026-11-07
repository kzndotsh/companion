"""The commands that can first label or write with a model before they print: `map`, `lore` and
`episodes`. Their reports are the features' own (`cli.py` in each)."""

from __future__ import annotations

import argparse
import asyncio

from companion import commands
from companion.features.curiosity.map import cli as knowing
from companion.features.episodes import cli as episodes
from companion.features.lore import cli as lore
from companion.kit.command import Command, Group, db_args, emit, target


def _map_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--label", action="store_true", help="label new memories first (a model call)")
    db_args(p)


def _map(a: argparse.Namespace) -> int:
    db, rel = target(a)
    first = asyncio.run(commands.run(db, rel, knowing.label_now)) if a.label else ""
    return emit(first + knowing.run(db, rel) + "\n")


def _lore_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--label", action="store_true", help="label its new views first (a model call)")
    p.add_argument("--relabel", action="store_true", help="label every view again (model calls)")
    db_args(p)


def _lore(a: argparse.Namespace) -> int:
    db, rel = target(a)
    first = (
        asyncio.run(commands.run(db, rel, lambda x: lore.label_now(x, again=a.relabel)))
        if a.label or a.relabel
        else ""
    )
    return emit(first + lore.run(db, rel))


def _episodes_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--write", action="store_true", help="write the ones not written yet (a model call)"
    )
    db_args(p)


def _episodes(a: argparse.Namespace) -> int:
    db, rel = target(a)
    first = asyncio.run(commands.run(db, rel, episodes.write_now)) if a.write else ""
    return emit(first + episodes.run(db, rel))


COMMANDS = (
    Command(
        "map",
        Group.MEMORY,
        "what it knows about them by part of their life, and the gap it would ask",
        _map,
        _map_args,
    ),
    Command(
        "lore",
        Group.ITSELF,
        "its own lore: the views it holds that are tastes (ADR 0020)",
        _lore,
        _lore_args,
    ),
    Command(
        "episodes",
        Group.DAYS,
        "the times they spent together, with a line about each",
        _episodes,
        _episodes_args,
    ),
)
