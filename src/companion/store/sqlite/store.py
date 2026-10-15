"""One relationship's file, behind a handle so callers never touch sqlite3."""

from __future__ import annotations

from pathlib import Path

from companion.core.prompt.prefix import Prefix
from companion.core.replay import TurnRecord
from companion.core.types import Decision, RelationshipId, SessionId, Utterance
from companion.store.sqlite import decisions, ledger, turns
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

    def session_utterances(self, rel: RelationshipId, session: SessionId) -> list[Utterance]:
        return ledger.session_utterances(self._conn, rel, session)

    def save_prefix(self, p: Prefix) -> None:
        turns.save_prefix(self._conn, p)

    def record_turn(self, r: TurnRecord) -> None:
        turns.record_turn(self._conn, r)

    def append_decision(self, d: Decision) -> None:
        decisions.append_decision(self._conn, d)
