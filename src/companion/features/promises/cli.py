"""`companion promises`: the promises the companion made in its own replies (J12, shadow), newest
first, each lasting or about a moment. `--not ID` marks one as not a promise and `--retire ID`
retires one; both are recorded, never deleted, and a marked promise leaves the list. `--moment ID`
and `--lasting ID` relabel how long one lasts; a moment's promise binds for a week."""

from __future__ import annotations

import argparse
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.types import RelationshipId
from companion.features.promises.logic import Scope, in_force
from companion.features.promises.store import Promises
from companion.kit.command import Command, Group, db_args, emit, target
from companion.store.sqlite.store import Store

SHOWN = 30


def run(  # noqa: PLR0913
    db: Path,
    relationship: str,
    *,
    wrong: str | None = None,
    retire: str | None = None,
    moment: str | None = None,
    lasting: str | None = None,
) -> str:
    rel = RelationshipId(relationship)
    with Store(db) as store:
        current = [r for r in store.part(Promises).recorded(rel) if r.mark is None]
        if moment or lasting:
            prefix, scope = (moment, Scope.MOMENT) if moment else (lasting, Scope.LASTING)
            found = [r for r in current if r.promise.id.startswith(str(prefix))]
            if len(found) != 1:
                return f"{len(found)} current promises start with {prefix!r}; need exactly one\n"
            store.part(Promises).set_scope(found[0].promise.id, scope, "owner", utc_now())
            return f"now {scope}: {found[0].promise.quote}\n"
        if wrong or retire:
            prefix, mark = (wrong, "not_a_promise") if wrong else (retire, "retired")
            found = [r for r in current if r.promise.id.startswith(str(prefix))]
            if len(found) != 1:
                return f"{len(found)} current promises start with {prefix!r}; need exactly one\n"
            store.part(Promises).mark(found[0].promise.id, mark, "the owner said so", utc_now())
            return f"marked {mark.replace('_', ' ')}: {found[0].promise.quote}\n"
        if not current:
            return "no promises recorded\n"
        now = utc_now()
        lines: list[str] = []
        for r in reversed(current[-SHOWN:]):
            p = r.promise
            word = f"  avoid {p.avoid!r}" if p.avoid else ""
            ended = "" if in_force(p, now) else "  (its moment has passed)"
            head = f"{p.id[:8]}  {p.at:%a %d %b %H:%M}  {p.kind:8} {p.scope:7}{word}{ended}"
            lines.append(f"{head}\n  {p.quote}")
        return "\n".join(lines) + "\n"


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--not", dest="wrong", metavar="ID", help="mark one as not a promise")
    p.add_argument("--retire", metavar="ID", help="retire one")
    p.add_argument("--moment", metavar="ID", help="mark one as about a moment: it binds a week")
    p.add_argument("--lasting", metavar="ID", help="mark one as lasting until released")
    db_args(p)


COMMANDS = (
    Command(
        "promises",
        Group.ITSELF,
        "the promises it made in its own replies, newest first",
        lambda a: emit(
            run(*target(a), wrong=a.wrong, retire=a.retire, moment=a.moment, lasting=a.lasting)
        ),
        _args,
    ),
)
