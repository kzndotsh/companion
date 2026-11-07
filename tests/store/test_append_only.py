"""Every table in a fresh database is append-only, or is named here with why it is not."""

from __future__ import annotations

import re
from pathlib import Path

from companion.store.sqlite.db import open_db

# Tables meant to change. A new table is append-only unless it is added here with a reason.
UPDATED = {
    # Closing a belief sets `valid_until`; triggers keep the claim fixed and a closure final.
    "beliefs",
    # An id-to-turn lookup (a /flag or /fav reply finds its turn), written with INSERT OR IGNORE.
    # It holds no evidence, so ADR 0002 does not list it.
    "sent_messages",
    "received_messages",
    # The migration runner's own bookkeeping.
    "schema_version",
}


def _aborting(sql: str, kind: str, table: str) -> bool:
    return bool(re.search(rf"BEFORE {kind}\s+ON\s+{table}\b", sql)) and "RAISE" in sql


def test_every_table_is_append_only_or_named(tmp_path: Path) -> None:
    conn = open_db(tmp_path / "x.db")
    tables = {
        str(r["name"])
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    triggers = [
        str(r["sql"]) for r in conn.execute("SELECT sql FROM sqlite_master WHERE type = 'trigger'")
    ]
    open_tables = sorted(
        t
        for t in tables - UPDATED
        if not (
            any(_aborting(s, "UPDATE", t) for s in triggers)
            and any(_aborting(s, "DELETE", t) for s in triggers)
        )
    )
    assert not open_tables, (
        f"tables that can be updated or deleted, and are not named: {open_tables}"
    )
    assert tables >= UPDATED, f"named tables that do not exist: {sorted(UPDATED - tables)}"
