"""Database snapshots and restore (J36). SQLite's online backup copies a consistent database even
while the bot is writing; every copy is checked before it counts, and a restore never touches the
live file until the copy it will use has passed the same check."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path


class BackupError(Exception):
    pass


def check(path: Path) -> int:
    """The number of messages in a database file, after its integrity check passes."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        result = conn.execute("PRAGMA quick_check").fetchone()
        if result is None or result[0] != "ok":
            msg = f"{path.name} failed its integrity check: {result}"
            raise BackupError(msg)
        return int(conn.execute("SELECT COUNT(*) FROM utterances").fetchone()[0])
    except sqlite3.DatabaseError as err:
        msg = f"{path.name} could not be read: {err}"
        raise BackupError(msg) from err
    finally:
        conn.close()


def _copy(source: Path, target: Path) -> None:
    """Copy a database; a failure removes the half-written target and raises BackupError."""
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
        dst.execute("PRAGMA journal_mode = DELETE")  # one self-contained file, no -wal beside it
    except sqlite3.DatabaseError as err:
        dst.close()
        target.unlink(missing_ok=True)
        msg = f"{source.name} could not be copied: {err}"
        raise BackupError(msg) from err
    finally:
        dst.close()
        src.close()


def snapshot(db: Path, into: Path, tag: str, now: datetime) -> tuple[Path, int]:
    """Copy the database to `into`, check the copy, and return it with its message count. A copy
    that fails the check is removed and the error raised."""
    into.mkdir(parents=True, exist_ok=True)
    final = into / f"{db.stem}-{now:%Y%m%d-%H%M%S}-{tag}.sqlite"
    partial = final.with_suffix(".partial")
    _copy(db, partial)
    try:
        n = check(partial)
    except BackupError:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(final)
    return final, n


def snapshots(into: Path, stem: str) -> list[Path]:
    """This database's snapshots, oldest first."""
    return sorted(into.glob(f"{stem}-*.sqlite"))


def prune(into: Path, stem: str, keep: int, *, daily: bool) -> list[Path]:
    """Remove all but the newest `keep` snapshots of one kind: the daily ones, or the rest (taken at
    a start, by hand, or before a restore). Kept apart so frequent restarts never push the older
    daily history out. Only snapshot files are ever removed; the live database is never touched."""
    mine = [p for p in snapshots(into, stem) if p.stem.endswith("-daily") == daily]
    old = mine[:-keep] if keep > 0 else []
    for path in old:
        path.unlink()
    return old


def restore(backup: Path, live: Path, into: Path, now: datetime) -> Path:
    """Put a snapshot back as the live database. The bot must be stopped. The current database is
    snapshotted first, and the backup is copied and checked beside the live file before it replaces
    it, so a bad backup leaves everything as it was. Returns the pre-restore snapshot."""
    check(backup)
    keep = live
    if live.exists():
        conn = sqlite3.connect(str(live))
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            conn.close()
        keep, _ = snapshot(live, into, "before-restore", now)
    staged = live.with_suffix(".restoring")
    staged.unlink(missing_ok=True)
    _copy(backup, staged)
    try:
        check(staged)
    except BackupError:
        staged.unlink(missing_ok=True)
        raise
    for side in ("-wal", "-shm"):
        Path(f"{live}{side}").unlink(missing_ok=True)  # emptied by the checkpoint above
    os.replace(staged, live)
    return keep
