"""`companion backup`: snapshot the database and character sheets now, `--list` the snapshots, or
`--restore FILE` to put one back (the bot must be stopped; the current database is kept first)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from companion import backups
from companion.core.clock import utc_now
from companion.store.sqlite.backup import BackupError, check, restore, snapshots

BOT = r"(^uv run companion run$|\.venv/bin/companion run$)"  # as scripts/restart.sh finds it


def _bot_running() -> bool:
    found = subprocess.run(  # noqa: S603  # a fixed pattern, no user input
        ["pgrep", "-f", BOT],  # noqa: S607  # pgrep from PATH, as scripts/restart.sh uses it
        capture_output=True,
        check=False,
    )
    return found.returncode == 0


def run(db: Path, *, listing: bool = False, restore_from: Path | None = None) -> str:
    data = db.parent
    into = backups.backup_dir(data)
    if listing:
        found = snapshots(into, db.stem)
        if not found:
            return f"no snapshots in {into}"
        return "\n".join(f"{p.name}  {p.stat().st_size // 1024} KB" for p in found)
    try:
        if restore_from is None:
            return backups.back_up(data, db, "manual", utc_now())
        if _bot_running():
            return "the bot is running; stop it first (Ctrl-C in its tab), then restore"
        source = restore_from if restore_from.exists() else into / restore_from.name
        n = check(source)
        kept = restore(source, db, into, utc_now())
    except BackupError as err:
        return f"nothing changed: {err}"
    return f"restored {source.name} ({n} messages); the database before it is kept as {kept.name}"
