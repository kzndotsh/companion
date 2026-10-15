"""Which relationship a command acts on, so you rarely have to say."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_db(arg: Path | None, data: Path = Path("data")) -> Path:
    """--db, else $COMPANION_DB, else the one database in data/."""
    if arg is not None:
        return arg
    env = os.environ.get("COMPANION_DB")
    if env:
        return Path(env)
    found = sorted(data.glob("*.sqlite"))
    if len(found) == 1:
        return found[0]
    if not found:
        msg = f"no database in {data}/. Pass --db or set COMPANION_DB."
    else:
        names = ", ".join(p.name for p in found)
        msg = f"several databases in {data}/ ({names}). Pass --db or set COMPANION_DB."
    raise SystemExit(msg)


def resolve_relationship(arg: str | None, db: Path) -> str:
    """--relationship, else the database's file name, which is how the daemon names it."""
    return arg or db.stem


def find_db(arg: Path | None, data: Path = Path("data")) -> Path | None:
    """Like resolve_db, but None when there is no database, for commands that can work without."""
    try:
        return resolve_db(arg, data)
    except SystemExit:
        return None
