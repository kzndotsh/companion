from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from companion import daemon
from companion.cli import beliefs, flags, replay
from companion.cli.target import resolve_db, resolve_relationship


def _db_args(p: argparse.ArgumentParser, *, relationship: bool = True) -> None:
    p.add_argument(
        "--db", type=Path, help="the relationship's SQLite file (default: the one in data/)"
    )
    if relationship:
        p.add_argument("--relationship", help="default: the database's file name")


def _target(a: argparse.Namespace) -> tuple[Path, str]:
    db = resolve_db(a.db)
    return db, resolve_relationship(getattr(a, "relationship", None), db)


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

    _db_args(sub.add_parser("rebuild", help="restate every belief under the current rules"))
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
    out, code = replay.run(resolve_db(a.db), str(a.turn_id))
    (sys.stdout if code != 2 else sys.stderr).write(out)
    return code


def _reflect(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    return _out(asyncio.run(daemon.reflect_now(db, rel, from_start=bool(a.from_start))))


def _run(a: argparse.Namespace) -> int:
    try:
        asyncio.run(daemon.run(Path(a.data)))
    except KeyboardInterrupt:
        sys.stderr.write("stopped\n")
    return 0


def _rebuild(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    return _out(asyncio.run(daemon.rebuild_now(db, rel)))


def _flags(a: argparse.Namespace) -> int:
    return _out(flags.run(*_target(a)))


def _beliefs(a: argparse.Namespace) -> int:
    return _out(beliefs.run(*_target(a)))


def _dedupe(a: argparse.Namespace) -> int:
    return _out(beliefs.dedupe(*_target(a)))


def _retire(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    return _out(beliefs.retire_one(db, rel, str(a.id_prefix), str(a.reason)))


HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "replay": _replay,
    "flags": _flags,
    "beliefs": _beliefs,
    "dedupe": _dedupe,
    "retire": _retire,
    "reflect": _reflect,
    "rebuild": _rebuild,
    "run": _run,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return HANDLERS[str(args.command)](args)
