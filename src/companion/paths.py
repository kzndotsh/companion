"""Where the bot's files are: the data folder and the database in it, built once and handed on.

The bot's data folder is `companion run --data`, and its database is `companion.sqlite` in it. A
command that is given a database (`--db`, `COMPANION_DB`, or the one in `data/`, `kit/target.py`)
takes the folder that holds it as the data folder, so its sheets, backups and logs are the ones
beside that database. Nothing else spells `DATABASE`, `data / "backups"` or `db.parent`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DATABASE = "companion.sqlite"  # in the data folder, whichever platform it runs on


@dataclass(frozen=True, slots=True)
class Paths:
    data: Path
    db: Path

    @classmethod
    def in_(cls, data: Path) -> Paths:
        """The bot's: its database is `companion.sqlite` in the data folder."""
        return cls(data, data / DATABASE)

    @classmethod
    def beside(cls, db: Path) -> Paths:
        """A command's: the data folder is the one holding the database it was given."""
        return cls(db.parent, db)

    @property
    def logs(self) -> Path:
        return self.data / "logs"

    def backups(self, given: Path | None) -> Path:
        """Where snapshots go: `given` (COMPANION_BACKUP_DIR), else `backups/` in the data folder"""
        return given or self.data / "backups"
