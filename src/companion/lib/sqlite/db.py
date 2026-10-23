"""An SQLite file: WAL, foreign keys, a single writer via BEGIN IMMEDIATE, and numbered migrations
read from a folder the caller names."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib.resources.abc import Traversable
from pathlib import Path

BUSY_TIMEOUT_MS = 5000


def iso(value: datetime) -> str:
    """Canonical UTC text form. Fixed width, so string order equals time order."""
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def write_tx(conn: sqlite3.Connection) -> Generator[sqlite3.Connection]:
    """The only way to write. BEGIN IMMEDIATE takes the writer lock up front, so a deferred
    upgrade can never ignore the busy timeout."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def _migration_files(root: Traversable) -> list[tuple[int, str, str]]:
    found: list[tuple[int, str, str]] = []
    for entry in root.iterdir():
        name = entry.name
        if name.endswith(".sql"):
            found.append((int(name.split("_", 1)[0]), name, entry.read_text(encoding="utf-8")))
    return sorted(found)


def migrate(conn: sqlite3.Connection, root: Traversable) -> list[str]:
    """Apply the numbered `.sql` files in `root` not yet recorded. Returns the names applied."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version"
        " (version INTEGER PRIMARY KEY, name TEXT NOT NULL)"
    )
    done = {int(r["version"]) for r in conn.execute("SELECT version FROM schema_version")}
    applied: list[str] = []
    for version, name, sql in _migration_files(root):
        if version in done:
            continue
        record = f"INSERT INTO schema_version (version, name) VALUES ({version}, '{name}');"  # noqa: S608
        try:
            conn.executescript(f"BEGIN IMMEDIATE;\n{sql}\n{record}\nCOMMIT;")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        applied.append(name)
    return applied
