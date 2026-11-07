from __future__ import annotations

import argparse
import asyncio
import shutil
import textwrap
from collections.abc import Sequence

from companion import commands
from companion.cli import (
    address,
    audit,
    backup,
    beliefs,
    favorites,
    flags,
    initiative,
    memory,
    replay,
    shadows,
    spend,
)
from companion.cli import crisis as crisis_cli
from companion.cli import eval as eval_cli
from companion.cli import prompts as prompts_cli
from companion.cli import run as run_cli
from companion.features.calendar import cli as calendar
from companion.features.curiosity.map import cli as knowing
from companion.features.episodes import cli as episodes
from companion.features.history import cli as history
from companion.features.intimate import cli as intimate
from companion.features.lore import cli as lore
from companion.features.mood import cli as mood
from companion.features.now import cli as now_cli
from companion.features.promises import cli as promises
from companion.features.reminders import cli as reminders
from companion.kit.command import Command, Group, Job, target

# Every module that declares commands (`COMMANDS`). A new command is one `Command` in its module;
# a new module is one line here. The order is the order of `companion --help` within a heading.
MODULES = (
    run_cli,
    shadows,
    spend,
    prompts_cli,
    backup,
    flags,
    favorites,
    replay,
    beliefs,
    memory,
    knowing,
    lore,
    episodes,
    address,
    now_cli,
    reminders,
    calendar,
    history,
    promises,
    mood,
    initiative,
    intimate,
    audit,
    crisis_cli,
    eval_cli,
)
COMMANDS: tuple[Command, ...] = tuple(c for m in MODULES for c in m.COMMANDS)
BY_NAME: dict[str, Command] = {c.name: c for c in COMMANDS}


class _Parser(argparse.ArgumentParser):
    """The top-level parser, whose help lists the commands by heading, one per line."""

    def format_help(self) -> str:
        width = min(shutil.get_terminal_size().columns, 100)
        name_w = max(len(c.name) for c in COMMANDS) + 2
        lines = ["usage: companion COMMAND [options]", ""]
        for group in Group:
            lines.append(f"{group}:")
            for command in (c for c in COMMANDS if c.group is group):
                wrapped = textwrap.wrap(command.help, max(width - name_w - 2, 30))
                lines.append(f"  {command.name:<{name_w}}{wrapped[0] if wrapped else ''}")
                lines.extend(f"  {'':<{name_w}}{more}" for more in wrapped[1:])
            lines.append("")
        lines.append("companion COMMAND --help shows one command's options.")
        return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="companion", add_help=True)
    sub = parser.add_subparsers(
        dest="command", required=True, metavar="COMMAND", parser_class=argparse.ArgumentParser
    )
    for command in COMMANDS:
        command.args(sub.add_parser(command.name, help=command.help))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return _run(BY_NAME[str(args.command)], args)


def _run(command: Command, args: argparse.Namespace) -> int:
    if command.run is not None:
        return command.run(args)
    assert command.serving is not None

    def serve(job: Job) -> str:
        db, rel = target(args)
        return asyncio.run(commands.run(db, rel, job))

    return command.serving(args, serve)
