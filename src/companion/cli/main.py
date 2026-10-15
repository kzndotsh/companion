from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from companion.cli import replay


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="companion")
    sub = parser.add_subparsers(dest="command", required=True)
    rp = sub.add_parser("replay", help="rebuild what the fast loop saw for one turn")
    rp.add_argument("turn_id")
    rp.add_argument("--db", type=Path, required=True, help="the relationship's SQLite file")
    args = parser.parse_args(argv)
    if args.command == "replay":
        out, code = replay.run(Path(args.db), str(args.turn_id))
        (sys.stdout if code != 2 else sys.stderr).write(out)
        return code
    return 2
