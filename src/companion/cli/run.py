"""`companion run`: talk to the companion on the chat platform."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from companion import daemon
from companion.kit.command import Command, Group
from companion.settings import DATA_DIR


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--data", type=Path, default=DATA_DIR)


def _run(a: argparse.Namespace) -> int:
    try:
        asyncio.run(daemon.run(Path(a.data)))
    except KeyboardInterrupt:
        sys.stderr.write("stopped\n")
    return 0


COMMANDS = (
    Command(
        "run",
        Group.RUNNING,
        "talk to the companion on Telegram, or on Discord with COMPANION_PLATFORM=discord",
        _run,
        _args,
    ),
)
