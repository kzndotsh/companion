"""One SQLite file per relationship, migrated from this package's own `migrations/` folder."""

from __future__ import annotations

import sqlite3
from importlib import resources
from pathlib import Path

from companion.lib.sqlite import db

MIGRATIONS = resources.files("companion.store.sqlite") / "migrations"


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply the companion's migrations not yet recorded. Returns the names applied."""
    return db.migrate(conn, MIGRATIONS)


def open_db(path: Path) -> sqlite3.Connection:
    """The relationship's database, connected and migrated."""
    conn = db.connect(path)
    migrate(conn)
    return conn
