from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

from companion import daemon
from companion.cli import replay


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="companion")
    sub = parser.add_subparsers(dest="command", required=True)
    rp = sub.add_parser("replay", help="rebuild what the fast loop saw for one turn")
    rp.add_argument("turn_id")
    rp.add_argument("--db", type=Path, required=True, help="the relationship's SQLite file")
    run = sub.add_parser("run", help="talk to the companion on Telegram")
    run.add_argument("--data", type=Path, default=Path("data"))
    args = parser.parse_args(argv)
    if args.command == "run":
        asyncio.run(daemon.run(Path(args.data)))
        return 0
    if args.command == "replay":
        out, code = replay.run(Path(args.db), str(args.turn_id))
        (sys.stdout if code != 2 else sys.stderr).write(out)
        return code
    return 2
