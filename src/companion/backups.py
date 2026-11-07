"""Backups of everything the bot cannot rebuild (J36): the database and the private character
sheets. The persona and prompts are in git, and `.env` is left out so secrets are not copied
around. Snapshots go to `data/backups/`, or COMPANION_BACKUP_DIR (another drive or a synced folder,
since a copy on the same disk does not survive the disk)."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from companion import characters
from companion.lib.sqlite.backup import BackupError, prune, snapshot
from companion.paths import Paths

log = logging.getLogger("companion.backup")
KEEP_DAILY = 7  # a week of history, however often it restarts
KEEP_RECENT = 7  # snapshots taken at a start, by hand or before a restore
EVERY_SECONDS = 24 * 3600


def back_up(paths: Paths, tag: str, now: datetime, into: Path) -> str:
    """Snapshot the database and the character sheets, keep the newest of each kind (KEEP_DAILY
    daily, KEEP_RECENT of the rest), and say what happened. Raises BackupError when the database
    copy fails its check."""
    db = paths.db
    if not db.exists():
        return f"no database at {db}, nothing to back up"
    path, n = snapshot(db, into, tag, now)
    daily = tag == "daily"
    keep = KEEP_DAILY if daily else KEEP_RECENT
    removed = prune(into, db.stem, keep, daily=daily)
    sheets = characters.sheets_dir(paths.data)
    if sheets.is_dir():
        shutil.copytree(sheets, into / f"characters-{now:%Y%m%d-%H%M%S}-{tag}")
        mine = [p for p in sorted(into.glob("characters-*")) if p.name.endswith("-daily") == daily]
        for old in mine[:-keep]:
            shutil.rmtree(old)
    return f"backed up {n} messages to {path}" + (
        f"; removed {len(removed)} older snapshots" if removed else ""
    )


def back_up_quietly(paths: Paths, tag: str, now: datetime, into: Path) -> None:
    """For the bot itself: a failed backup is logged loudly and never stops it."""
    try:
        log.info("%s", back_up(paths, tag, now, into))
    except (BackupError, OSError):
        log.exception(
            "BACKUP FAILED (%s); the bot carries on, run `companion backup` to retry", tag
        )
