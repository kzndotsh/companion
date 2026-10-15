from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from companion import daemon
from companion.cli import beliefs, flags, replay


def _db_args(p: argparse.ArgumentParser, *, relationship: bool = True) -> None:
    p.add_argument("--db", type=Path, required=True, help="the relationship's SQLite file")
    if relationship:
        p.add_argument("--relationship", required=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="companion")
    sub = parser.add_subparsers(dest="command", required=True)

    rp = sub.add_parser("replay", help="rebuild what the fast loop saw for one turn")
    rp.add_argument("turn_id")
    _db_args(rp, relationship=False)

    _db_args(sub.add_parser("flags", help="list the turns you flagged"))
    _db_args(sub.add_parser("beliefs", help="what it currently believes, with quotes"))
    _db_args(sub.add_parser("dedupe", help="close beliefs that rest on the same words"))

    rt = sub.add_parser("retire", help="close one belief by id prefix, with a reason")
    rt.add_argument("id_prefix")
    rt.add_argument("--reason", required=True)
    _db_args(rt)

    rf = sub.add_parser("reflect", help="run one slow-loop pass now")
    rf.add_argument("--from-start", action="store_true", help="re-read the whole conversation")
    _db_args(rf)

    run = sub.add_parser("run", help="talk to the companion on Telegram")
    run.add_argument("--data", type=Path, default=Path("data"))
    return parser


def _out(text: str) -> int:
    sys.stdout.write(text)
    return 0


def _replay(a: argparse.Namespace) -> int:
    out, code = replay.run(Path(a.db), str(a.turn_id))
    (sys.stdout if code != 2 else sys.stderr).write(out)
    return code


def _reflect(a: argparse.Namespace) -> int:
    return _out(
        asyncio.run(
            daemon.reflect_now(Path(a.db), str(a.relationship), from_start=bool(a.from_start))
        )
    )


def _run(a: argparse.Namespace) -> int:
    try:
        asyncio.run(daemon.run(Path(a.data)))
    except KeyboardInterrupt:
        sys.stderr.write("stopped\n")
    return 0


HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "replay": _replay,
    "flags": lambda a: _out(flags.run(Path(a.db), str(a.relationship))),
    "beliefs": lambda a: _out(beliefs.run(Path(a.db), str(a.relationship))),
    "dedupe": lambda a: _out(beliefs.dedupe(Path(a.db), str(a.relationship))),
    "retire": lambda a: _out(
        beliefs.retire_one(Path(a.db), str(a.relationship), str(a.id_prefix), str(a.reason))
    ),
    "reflect": _reflect,
    "run": _run,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return HANDLERS[str(args.command)](args)
