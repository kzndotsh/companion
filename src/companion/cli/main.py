from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

from companion import daemon
from companion.cli import beliefs, flags, replay


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="companion")
    sub = parser.add_subparsers(dest="command", required=True)
    rp = sub.add_parser("replay", help="rebuild what the fast loop saw for one turn")
    rp.add_argument("turn_id")
    rp.add_argument("--db", type=Path, required=True, help="the relationship's SQLite file")
    fl = sub.add_parser("flags", help="list the turns you flagged")
    fl.add_argument("--db", type=Path, required=True)
    fl.add_argument("--relationship", required=True)
    bl = sub.add_parser("beliefs", help="what it currently believes, with quotes")
    bl.add_argument("--db", type=Path, required=True)
    bl.add_argument("--relationship", required=True)
    rf = sub.add_parser("reflect", help="run one slow-loop pass now")
    rf.add_argument("--db", type=Path, required=True)
    rf.add_argument("--relationship", required=True)
    rf.add_argument("--from-start", action="store_true", help="re-read the whole conversation")
    run = sub.add_parser("run", help="talk to the companion on Telegram")
    run.add_argument("--data", type=Path, default=Path("data"))
    args = parser.parse_args(argv)
    if args.command == "beliefs":
        sys.stdout.write(beliefs.run(Path(args.db), str(args.relationship)))
        return 0
    if args.command == "reflect":
        sys.stdout.write(
            asyncio.run(
                daemon.reflect_now(
                    Path(args.db), str(args.relationship), from_start=bool(args.from_start)
                )
            )
        )
        return 0
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
