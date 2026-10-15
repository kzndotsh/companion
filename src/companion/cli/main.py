from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

from companion import daemon
from companion.cli import flags, replay


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="companion")
    sub = parser.add_subparsers(dest="command", required=True)
    rp = sub.add_parser("replay", help="rebuild what the fast loop saw for one turn")
    rp.add_argument("turn_id")
    rp.add_argument("--db", type=Path, required=True, help="the relationship's SQLite file")
    fl = sub.add_parser("flags", help="list the turns you flagged")
    fl.add_argument("--db", type=Path, required=True)
    fl.add_argument("--relationship", required=True)
    run = sub.add_parser("run", help="talk to the companion on Telegram")
    run.add_argument("--data", type=Path, default=Path("data"))
    args = parser.parse_args(argv)
    if args.command == "flags":
        sys.stdout.write(flags.run(Path(args.db), str(args.relationship)))
        return 0
    if args.command == "run":
        try:
            asyncio.run(daemon.run(Path(args.data)))
        except KeyboardInterrupt:
            sys.stderr.write("stopped\n")
        return 0
    if args.command == "replay":
        out, code = replay.run(Path(args.db), str(args.turn_id))
        (sys.stdout if code != 2 else sys.stderr).write(out)
        return code
    return 2
