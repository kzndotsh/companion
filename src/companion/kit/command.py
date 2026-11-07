"""What a command is, as `companion --help` and the parser see it: declared once, in the module
that does the work. A module exports `COMMANDS`, and `cli/main.py` lists the modules; a new command
is one `Command` here and nothing else to edit."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from companion.kit.target import resolve_db, resolve_relationship


class Group(StrEnum):
    """The headings of `companion --help`, in the order they are listed."""

    RUNNING = "Running it"
    FLAGS = "Your flags and favorites"
    MEMORY = "What it remembers about you"
    DAYS = "Your days: plans, reminders, occasions"
    ITSELF = "The companion itself: tastes, past, promises, mood"
    REACH = "Messaging you first, and intimate scenes"
    MEASURING = "Measuring"


def db_args(p: argparse.ArgumentParser, *, relationship: bool = True) -> None:
    p.add_argument(
        "--db", type=Path, help="the relationship's SQLite file (default: the one in data/)"
    )
    if relationship:
        p.add_argument("--relationship", help="default: the database's file name")


def target(a: argparse.Namespace) -> tuple[Path, str]:
    """The database and the relationship a command acts on, from `--db` and `--relationship`."""
    db = resolve_db(a.db)
    return db, resolve_relationship(getattr(a, "relationship", None), db)


def emit(text: str) -> int:
    sys.stdout.write(text)
    return 0


@dataclass(frozen=True, slots=True)
class Command:
    """One command: its name, the heading it is listed under, its one-line help, how it reads its
    arguments (`--db` and `--relationship` unless it says otherwise) and what it does, returning
    the exit code."""

    name: str
    group: Group
    help: str
    run: Callable[[argparse.Namespace], int]
    args: Callable[[argparse.ArgumentParser], None] = db_args


def plain(name: str, group: Group, says: str, show: Callable[[Path, str], str]) -> Command:
    """A command that only prints a report of the relationship: `show(db, relationship)`."""
    return Command(name, group, says, lambda a: emit(show(*target(a))))


def no_args(p: argparse.ArgumentParser) -> None:
    """For a command that takes none, and no database."""
    del p
