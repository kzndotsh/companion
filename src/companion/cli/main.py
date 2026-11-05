from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
import textwrap
from collections.abc import Callable, Sequence
from pathlib import Path

from companion import commands, daemon
from companion.cli import (
    address,
    backup,
    beliefs,
    favorites,
    flags,
    initiative,
    memory,
    replay,
    spend,
)
from companion.cli import crisis as crisis_cli
from companion.cli import eval as eval_cli
from companion.cli import prompts as prompts_cli
from companion.cli import shadows as shadows_cli
from companion.cli.target import find_db, resolve_db, resolve_relationship
from companion.core.views import ViewMode
from companion.evals.fixtures import load_fixtures
from companion.features.audits.callbacks import cli as callbacks
from companion.features.audits.invented import cli as invented
from companion.features.calendar import cli as calendar
from companion.features.crisis import cli as crisis
from companion.features.curiosity.map import cli as knowing
from companion.features.episodes import cli as episodes
from companion.features.history import cli as history
from companion.features.intimate import cli as scene
from companion.features.lore import cli as lore
from companion.features.mood import cli as mood
from companion.features.now import cli as now_cli
from companion.features.promises import cli as promises
from companion.features.reminders import cli as reminders
from companion.features.upkeep.context import cli as context
from companion.features.upkeep.merging import cli as merging
from companion.features.upkeep.sort import cli as worth


def _db_args(p: argparse.ArgumentParser, *, relationship: bool = True) -> None:
    p.add_argument(
        "--db", type=Path, help="the relationship's SQLite file (default: the one in data/)"
    )
    if relationship:
        p.add_argument("--relationship", help="default: the database's file name")


def _target(a: argparse.Namespace) -> tuple[Path, str]:
    db = resolve_db(a.db)
    return db, resolve_relationship(getattr(a, "relationship", None), db)


def _state_commands(add: Callable[..., argparse.ArgumentParser]) -> None:
    """The commands that read or set what the bot carries between turns."""
    ad = add("address", help="how they want to be referred to, pinned in every card")
    ad.add_argument(
        "--set", dest="value", metavar="TEXT", help="record it; an empty text clears it"
    )
    _db_args(ad)
    bk = add(
        "backup", help="snapshot the database and character sheets now, or list or restore one"
    )
    bk.add_argument("--list", action="store_true", dest="listing", help="list the snapshots")
    bk.add_argument(
        "--restore", type=Path, metavar="FILE", help="put a snapshot back (bot stopped)"
    )
    _db_args(bk)
    mp = add("map", help="what it knows about them by part of their life, and the gap it would ask")
    mp.add_argument("--label", action="store_true", help="label new memories first (a model call)")
    _db_args(mp)
    lr = add("lore", help="its own lore: the views it holds that are tastes (ADR 0020)")
    lr.add_argument("--label", action="store_true", help="label its new views first (a model call)")
    lr.add_argument("--relabel", action="store_true", help="label every view again (model calls)")
    _db_args(lr)
    _db_args(add("history", help="the stories of its own past and their canon standing"))
    _db_args(add("intimate", help="the intimate memory lane by stance, and what is kept out"))
    pr = add("promises", help="the promises it made in its own replies, newest first")
    pr.add_argument("--not", dest="wrong", metavar="ID", help="mark one as not a promise")
    pr.add_argument("--retire", metavar="ID", help="retire one")
    pr.add_argument("--moment", metavar="ID", help="mark one as about a moment: it binds a week")
    pr.add_argument("--lasting", metavar="ID", help="mark one as lasting until released")
    _db_args(pr)
    ep = add("episodes", help="the times they spent together, with a line about each")
    ep.add_argument(
        "--write", action="store_true", help="write the ones not written yet (a model call)"
    )
    _db_args(ep)
    _db_args(add("calendar", help="the occasions in the next 30 days and what was offered lately"))
    _db_args(add("now", help="what they said is coming: the labels, what is open, the notes"))
    rm = add(
        "reminders", help="the reminders and repeating ones they asked for, and what became of each"
    )
    rm.add_argument("--cancel", metavar="ID", help="drop a pending one or stop a repeating one")
    _db_args(rm)
    md = add("mood", help="the mood now, or --replay DAYS of what it would have been")
    md.add_argument("--replay", type=int, metavar="DAYS", help="rebuild it over the last DAYS days")
    _db_args(md)


def _memory_commands(add: Callable[..., argparse.ArgumentParser]) -> None:
    """The commands that close or merge beliefs by hand, each closure logged with its reason."""
    mm = add("memory", help="answer the questions about memory, or propose merges (ADR 0019)")
    mm.add_argument("action", choices=["review", "group", "context", "label"])
    mm.add_argument(
        "--all", action="store_true", help="keep asking until none are left or you quit"
    )
    _db_args(mm)
    mg = add("merge", help="merge beliefs that say one thing into one, keeping every quote")
    mg.add_argument("id_prefix", nargs="+")
    mg.add_argument("--claim", required=True, help="the merged wording")
    _db_args(mg)
    rt = add("retire", help="close one belief, or retire a story of its past, by id prefix")
    rt.add_argument("id_prefix")
    rt.add_argument("--reason", required=True)
    _db_args(rt)


def _judging_commands(add: Callable[..., argparse.ArgumentParser]) -> None:
    """The commands that judge recent replies within a spend cap, then report."""
    au = add("audit", help="judge recent replies within a spend cap, then report")
    au.add_argument(
        "which",
        choices=("callbacks", "invented"),
        help="callbacks to memories, or made-up facts about them (G42)",
    )
    au.add_argument("--days", type=int, default=7)
    au.add_argument("--cap", type=float, default=0.10, help="stop judging at this much spend")
    au.add_argument(
        "--dump", type=Path, help="invented: write the candidates with their context, to confirm"
    )
    _db_args(au)
    cr = add("crisis", help="how often each crisis level was read lately, or --check the fixtures")
    cr.add_argument(
        "--check", action="store_true", help="read every crisis fixture three times (model calls)"
    )
    cr.add_argument("--cap", type=float, help="required with --check: stop at this much spend")
    cr.add_argument("--fixtures", type=Path, default=crisis.FIXTURES, help="the fixture file")
    _db_args(cr)


# Every command under one heading in `companion --help`; a test checks each is listed once.
GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Running it", ("run", "shadows", "spend", "prompts", "backup")),
    ("Your flags and favorites", ("flags", "favorites", "replay")),
    (
        "What it remembers about you",
        ("beliefs", "memory", "merge", "retire", "dedupe", "rebuild", "memory-pass", "map"),
    ),
    (
        "Your days: plans, reminders, occasions",
        ("address", "episodes", "now", "reminders", "calendar"),
    ),
    (
        "The companion itself: tastes, past, promises, mood",
        ("lore", "history", "promises", "opinions", "views", "approve", "mood"),
    ),
    ("Messaging you first, and intimate scenes", ("initiative", "intimate")),
    ("Measuring", ("audit", "crisis", "eval", "calibrate")),
)


class _Parser(argparse.ArgumentParser):
    """The top-level parser, whose help lists the commands by heading, one per line."""

    def __init__(self, helps: dict[str, str]) -> None:
        super().__init__(prog="companion", add_help=True)
        self.helps = helps

    def format_help(self) -> str:
        width = min(shutil.get_terminal_size().columns, 100)
        name_w = max(len(n) for n in self.helps) + 2
        lines = ["usage: companion COMMAND [options]", ""]
        for title, names in GROUPS:
            lines.append(f"{title}:")
            for name in names:
                wrapped = textwrap.wrap(self.helps.get(name, ""), max(width - name_w - 2, 30))
                lines.append(f"  {name:<{name_w}}{wrapped[0] if wrapped else ''}")
                lines.extend(f"  {'':<{name_w}}{more}" for more in wrapped[1:])
            lines.append("")
        lines.append("companion COMMAND --help shows one command's options.")
        return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    helps: dict[str, str] = {}
    parser = _Parser(helps)
    sub = parser.add_subparsers(
        dest="command", required=True, metavar="COMMAND", parser_class=argparse.ArgumentParser
    )

    def add(name: str, **kwargs: str) -> argparse.ArgumentParser:
        helps[name] = kwargs.get("help", "")
        return sub.add_parser(name, help=helps[name])

    rp = add("replay", help="rebuild what the reply path saw for one turn")
    rp.add_argument("turn_id")
    rp.add_argument(
        "--show-prompt",
        action="store_true",
        help="print everything the talker was sent, in order, with the persona in full",
    )
    _db_args(rp, relationship=False)

    fl = add("flags", help="list the turns you flagged")
    fl.add_argument("--to-fav", metavar="ID", help="move a flag (by flag or turn id) to favourites")
    _db_args(fl)
    _db_args(add("favorites", help="list the turns you loved"))
    _db_args(add("spend", help="what the paid calls cost, by purpose"))
    _db_args(add("initiative", help="open loops, and the messages it would send you first"))
    _state_commands(add)
    add("shadows", help="every feature in shadow, its review date and the overdue ones")
    pr = add("prompts", help="the current version of every prompt, or the text of one")
    pr.add_argument("which", nargs="?", help="a prompt name, optionally name@version")
    _db_args(add("beliefs", help="what it currently believes, with quotes"))
    vw = add("views", help="show or set how the companion's views reach the card")
    vw.add_argument("--mode", choices=[m.value for m in ViewMode])
    _db_args(vw)
    _db_args(add("calibrate", help="compare the automatic gates with your approvals"))
    _db_args(add("opinions", help="the companion's own views, tentative or settled"))
    _db_args(add("dedupe", help="close beliefs that rest on the same words"))

    ap = add("approve", help="approve one of the companion's own views, so it reaches the card")
    ap.add_argument("id_prefix")
    _db_args(ap)
    _memory_commands(add)

    _db_args(add("rebuild", help="restate every belief under the current rules"))
    _judging_commands(add)
    rf = add("memory-pass", help="run one memory pass now")
    rf.add_argument("--from-start", action="store_true", help="re-read the whole conversation")
    _db_args(rf)

    ev = add("eval", help="replay recorded turns against persona variants and score them")
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
    run = add(
        "run",
        help="talk to the companion on Telegram, or on Discord with COMPANION_PLATFORM=discord",
    )
    run.add_argument("--data", type=Path, default=Path("data"))
    return parser


def _out(text: str) -> int:
    sys.stdout.write(text)
    return 0


def _replay(a: argparse.Namespace) -> int:
    out, code = replay.run(resolve_db(a.db), str(a.turn_id), show_prompt=bool(a.show_prompt))
    (sys.stdout if code != 2 else sys.stderr).write(out)
    return code


def _memory_pass(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    return _out(asyncio.run(commands.memory_pass_now(db, rel, from_start=bool(a.from_start))))


def _run(a: argparse.Namespace) -> int:
    try:
        asyncio.run(daemon.run(Path(a.data)))
    except KeyboardInterrupt:
        sys.stderr.write("stopped\n")
    return 0


def _audit(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    days, cap = int(a.days), float(a.cap)
    if a.which == "invented":
        return _out(
            asyncio.run(commands.run(db, rel, lambda x: invented.judge_now(x, days, cap, a.dump)))
        )
    return _out(asyncio.run(commands.run(db, rel, lambda x: callbacks.judge_now(x, days, cap))))


def _crisis(a: argparse.Namespace) -> int:
    if not a.check:
        return _out(crisis.run(*_target(a)))
    if a.cap is None or a.cap <= 0:
        sys.stderr.write("pass --cap with --check, for example --cap 0.10; it costs money\n")
        return 2
    return _out(asyncio.run(crisis_cli.run(Path(a.fixtures), float(a.cap))))


def _rebuild(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    return _out(asyncio.run(commands.rebuild_now(db, rel)))


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


def _shadows(_: argparse.Namespace) -> int:
    return _out(shadows_cli.run())


def _prompts(a: argparse.Namespace) -> int:
    return _out(prompts_cli.run(a.which))


def _address(a: argparse.Namespace) -> int:
    return _out(address.run(*_target(a), a.value))


def _backup(a: argparse.Namespace) -> int:
    db, _ = _target(a)
    return _out(backup.run(db, listing=bool(a.listing), restore_from=a.restore) + "\n")


def _map(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    first = asyncio.run(commands.run(db, rel, knowing.label_now)) if a.label else ""
    return _out(first + knowing.run(db, rel) + "\n")


def _mood(a: argparse.Namespace) -> int:
    return _out(mood.run(*_target(a), a.replay))


def _initiative(a: argparse.Namespace) -> int:
    return _out(initiative.run(*_target(a)))


def _lore(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    first = (
        asyncio.run(commands.run(db, rel, lambda x: lore.label_now(x, again=a.relabel)))
        if a.label or a.relabel
        else ""
    )
    return _out(first + lore.run(db, rel))


def _history(a: argparse.Namespace) -> int:
    return _out(history.run(*_target(a)))


def _intimate(a: argparse.Namespace) -> int:
    return _out(scene.run(*_target(a)))


def _episodes(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    first = asyncio.run(commands.run(db, rel, episodes.write_now)) if a.write else ""
    return _out(first + episodes.run(db, rel))


def _reminders(a: argparse.Namespace) -> int:
    return _out(reminders.run(*_target(a), cancel=a.cancel))


def _calendar(a: argparse.Namespace) -> int:
    return _out(calendar.run(*_target(a)))


def _now(a: argparse.Namespace) -> int:
    return _out(now_cli.run(*_target(a)))


def _promises(a: argparse.Namespace) -> int:
    return _out(
        promises.run(
            *_target(a), wrong=a.wrong, retire=a.retire, moment=a.moment, lasting=a.lasting
        )
    )


def _favorites(a: argparse.Namespace) -> int:
    return _out(favorites.run(*_target(a)))


def _flags(a: argparse.Namespace) -> int:
    if a.to_fav:
        return _out(flags.to_favorite(*_target(a), str(a.to_fav)))
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


def _memory(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    if a.action == "group":
        return _out(asyncio.run(commands.run(db, rel, merging.group_now)))
    if a.action == "context":
        return _out(asyncio.run(commands.run(db, rel, context.write_now)))
    if a.action == "label":
        return _out(asyncio.run(commands.run(db, rel, worth.label_now)))
    return _out(memory.review(db, rel))


def _merge(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    return _out(beliefs.merge_some(db, rel, [str(x) for x in a.id_prefix], str(a.claim)))


def _retire(a: argparse.Namespace) -> int:
    db, rel = _target(a)
    return _out(beliefs.retire_one(db, rel, str(a.id_prefix), str(a.reason)))


HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "replay": _replay,
    "flags": _flags,
    "favorites": _favorites,
    "initiative": _initiative,
    "mood": _mood,
    "promises": _promises,
    "reminders": _reminders,
    "calendar": _calendar,
    "now": _now,
    "episodes": _episodes,
    "lore": _lore,
    "history": _history,
    "intimate": _intimate,
    "map": _map,
    "backup": _backup,
    "address": _address,
    "prompts": _prompts,
    "shadows": _shadows,
    "spend": _spend,
    "beliefs": _beliefs,
    "views": _views,
    "calibrate": _calibrate,
    "opinions": _opinions,
    "dedupe": _dedupe,
    "approve": _approve,
    "retire": _retire,
    "merge": _merge,
    "memory": _memory,
    "memory-pass": _memory_pass,
    "rebuild": _rebuild,
    "audit": _audit,
    "crisis": _crisis,
    "eval": _eval,
    "run": _run,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return HANDLERS[str(args.command)](args)
