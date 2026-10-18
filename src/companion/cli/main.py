from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from companion import daemon
from companion.cli import beliefs, favorites, flags, initiative, replay, spend
from companion.cli import eval as eval_cli
from companion.cli import prompts as prompts_cli
from companion.cli.target import find_db, resolve_db, resolve_relationship
from companion.core.views import ViewMode
from companion.evals.fixtures import load_fixtures


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
    rp.add_argument(
        "--show-prompt",
        action="store_true",
        help="print everything the talker was sent, in order, with the persona in full",
    )
    _db_args(rp, relationship=False)

    _db_args(sub.add_parser("flags", help="list the turns you flagged"))
    _db_args(sub.add_parser("favorites", help="list the turns you loved"))
    _db_args(sub.add_parser("spend", help="what the paid calls cost, by purpose"))
    _db_args(sub.add_parser("initiative", help="open loops and what shadow mode would send"))
    pr = sub.add_parser("prompts", help="the current version of every prompt, or the text of one")
    pr.add_argument("which", nargs="?", help="a prompt name, optionally name@version")
    _db_args(sub.add_parser("beliefs", help="what it currently believes, with quotes"))
    vw = sub.add_parser("views", help="show or set how the companion's views reach the card")
    vw.add_argument("--mode", choices=[m.value for m in ViewMode])
    _db_args(vw)
    _db_args(sub.add_parser("calibrate", help="compare the automatic gates with your approvals"))
    _db_args(sub.add_parser("opinions", help="the companion's own views, tentative or settled"))
    _db_args(sub.add_parser("dedupe", help="close beliefs that rest on the same words"))

    ap = sub.add_parser(
        "approve", help="approve one of the companion's own views, so it reaches the card"
    )
    ap.add_argument("id_prefix")
    _db_args(ap)
    rt = sub.add_parser("retire", help="close one belief by id prefix, with a reason")
    rt.add_argument("id_prefix")
    rt.add_argument("--reason", required=True)
    _db_args(rt)

    _db_args(sub.add_parser("rebuild", help="restate every belief under the current rules"))
    rf = sub.add_parser("reflect", help="run one slow-loop pass now")
    rf.add_argument("--from-start", action="store_true", help="re-read the whole conversation")
    _db_args(rf)

    ev = sub.add_parser(
        "eval", help="replay recorded turns against persona variants and score them"
    )
    ev.add_argument("--variants", default="", help="comma list: v10.md,v9.md,v10.md+nocard")
    ev.add_argument("--fixture", action="append", default=[], help="only this fixture id")
    ev.add_argument("--samples", type=int, default=3)
    ev.add_argument("--cap", type=float, default=0.10, help="stop at this much spend, in dollars")
    ev.add_argument(
        "--fixtures-dir",
        type=Path,
        action="append",
        default=[],
        help="default: evals/fixtures (public scripts) and evals/local (private recorded turns)",
    )
    ev.add_argument("--show", action="store_true", help="print every reply with its verdict")
    ev.add_argument("--dry-run", action="store_true", help="print the plan and estimate only")
    ev.add_argument("--list", action="store_true", help="list fixtures and exit")
    _db_args(ev, relationship=False)
    run = sub.add_parser("run", help="talk to the companion on Telegram")
    run.add_argument("--data", type=Path, default=Path("data"))
    return parser


def _out(text: str) -> int:
    sys.stdout.write(text)
    return 0


def _replay(a: argparse.Namespace) -> int:
    out, code = replay.run(resolve_db(a.db), str(a.turn_id), show_prompt=bool(a.show_prompt))
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


def _fixture_dirs(a: argparse.Namespace) -> tuple[Path, ...]:
    given = [Path(p) for p in a.fixtures_dir]
    return tuple(given) if given else (Path("evals/fixtures"), Path("evals/local"))


def _eval(a: argparse.Namespace) -> int:
    if a.list:
        return _out(eval_cli.describe(load_fixtures(*_fixture_dirs(a))))
    specs = [x.strip() for x in str(a.variants).split(",") if x.strip()]
    if not specs:
        sys.stderr.write("pass --variants, for example --variants v9.md,v10.md\n")
        return 2
    args = eval_cli.EvalArgs(
        find_db(a.db),
        _fixture_dirs(a),
        specs,
        list(a.fixture),
        int(a.samples),
        float(a.cap),
        bool(a.show),
        bool(a.dry_run),
    )
    out = asyncio.run(eval_cli.run(args))
    return _out(out)


def _spend(a: argparse.Namespace) -> int:
    return _out(spend.run(*_target(a)))


def _prompts(a: argparse.Namespace) -> int:
    return _out(prompts_cli.run(a.which))


def _initiative(a: argparse.Namespace) -> int:
    return _out(initiative.run(*_target(a)))


def _favorites(a: argparse.Namespace) -> int:
    return _out(favorites.run(*_target(a)))


def _flags(a: argparse.Namespace) -> int:
    return _out(flags.run(*_target(a)))


def _beliefs(a: argparse.Namespace) -> int:
    return _out(beliefs.run(*_target(a)))


def _views(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    return _out(beliefs.views_mode(db, rel, a.mode))


def _calibrate(a: argparse.Namespace) -> int:
    return _out(beliefs.calibrate(*_target(a)))


def _opinions(a: argparse.Namespace) -> int:
    return _out(beliefs.opinions(*_target(a)))


def _dedupe(a: argparse.Namespace) -> int:
    return _out(beliefs.dedupe(*_target(a)))


def _approve(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    return _out(beliefs.approve_one(db, rel, str(a.id_prefix)))


def _retire(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    return _out(beliefs.retire_one(db, rel, str(a.id_prefix), str(a.reason)))


HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "replay": _replay,
    "flags": _flags,
    "favorites": _favorites,
    "initiative": _initiative,
    "prompts": _prompts,
    "spend": _spend,
    "beliefs": _beliefs,
    "views": _views,
    "calibrate": _calibrate,
    "opinions": _opinions,
    "dedupe": _dedupe,
    "approve": _approve,
    "retire": _retire,
    "reflect": _reflect,
    "rebuild": _rebuild,
    "eval": _eval,
    "run": _run,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return HANDLERS[str(args.command)](args)
