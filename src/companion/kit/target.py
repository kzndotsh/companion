"""Which relationship a command acts on, so you rarely have to say."""

from __future__ import annotations

from pathlib import Path

from companion.settings import DATA_DIR, Settings
from companion.store.sqlite.store import FIRST_RELATIONSHIP, relationship_in


def resolve_db(arg: Path | None, data: Path = DATA_DIR) -> Path:
    """--db, else $COMPANION_DB, else the one database in data/."""
    if arg is not None:
        return arg
    configured = Settings.from_env().db
    if configured:
        return configured
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
    """--relationship, else the one relationship the database holds messages for, else the one a
    new database starts with."""
    return arg or relationship_in(db) or FIRST_RELATIONSHIP


def find_db(arg: Path | None, data: Path = DATA_DIR) -> Path | None:
    """Like resolve_db, but None when there is no database, for commands that can work without."""
    try:
        return resolve_db(arg, data)
    except SystemExit:
        return None
