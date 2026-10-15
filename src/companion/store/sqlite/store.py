"""One relationship's file, behind a handle so callers never touch sqlite3."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from companion.core.prompt.prefix import Prefix
from companion.core.replay import TurnRecord
from companion.core.types import Decision, Flag, RelationshipId, TurnId, Utterance
from companion.store.sqlite import decisions, flags, ledger, turns
from companion.store.sqlite.db import connect, migrate


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = connect(path)
        migrate(self._conn)

    def close(self) -> None:
        self._conn.close()

    def append_utterance(self, u: Utterance) -> None:
        ledger.append_utterance(self._conn, u)

    def history_before(self, rel: RelationshipId, before: datetime, limit: int) -> list[Utterance]:
        return ledger.history_before(self._conn, rel, before, limit)

    def save_prefix(self, p: Prefix) -> None:
        turns.save_prefix(self._conn, p)

    def record_turn(self, r: TurnRecord) -> None:
        turns.record_turn(self._conn, r)

    def append_decision(self, d: Decision) -> None:
        decisions.append_decision(self._conn, d)

    def latest_turn(self, rel: RelationshipId) -> TurnId | None:
        return turns.latest_turn(self._conn, rel)

    def add_flag(self, f: Flag) -> None:
        flags.add_flag(self._conn, f)

    def flags(self, rel: RelationshipId) -> list[Flag]:
        return flags.list_flags(self._conn, rel)
