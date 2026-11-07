from __future__ import annotations

from pathlib import Path

import pytest
from tests.conftest import T0

from companion.core.types import (
    Frame,
    RelationshipId,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.kit.target import resolve_db, resolve_relationship
from companion.store.sqlite.store import Store


def utterance(*, rel: RelationshipId, uid: str = "u1") -> Utterance:
    return Utterance(UtteranceId(uid), rel, TurnId(uid), Speaker.USER, "hi", Frame.REAL, "t", T0)


def test_an_explicit_db_wins(tmp_path: Path) -> None:
    (tmp_path / "a.sqlite").touch()
    assert resolve_db(Path("x.sqlite"), tmp_path) == Path("x.sqlite")


def test_the_only_database_in_data_is_used(tmp_path: Path) -> None:
    (tmp_path / "telegram-1.sqlite").touch()
    (tmp_path / "telegram-1.sqlite-wal").touch()
    assert resolve_db(None, tmp_path) == tmp_path / "telegram-1.sqlite"


def test_the_env_var_beats_the_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "a.sqlite").touch()
    monkeypatch.setenv("COMPANION_DB", "/elsewhere/b.sqlite")
    assert resolve_db(None, tmp_path) == Path("/elsewhere/b.sqlite")


def test_none_or_several_is_a_clear_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COMPANION_DB", raising=False)
    with pytest.raises(SystemExit, match="no database"):
        resolve_db(None, tmp_path)
    (tmp_path / "a.sqlite").touch()
    (tmp_path / "b.sqlite").touch()
    with pytest.raises(SystemExit, match="several"):
        resolve_db(None, tmp_path)


def test_relationship_is_the_one_the_database_holds(tmp_path: Path) -> None:
    db = tmp_path / "companion.sqlite"
    assert resolve_relationship(None, db) == "owner"  # no database yet
    store = Store(db)
    assert resolve_relationship(None, db) == "owner"  # no messages yet
    store.append_utterance(utterance(rel=RelationshipId("telegram-1")))
    store.close()
    assert resolve_relationship(None, db) == "telegram-1"
    assert resolve_relationship("other", db) == "other"


def test_a_database_with_two_relationships_asks_which(tmp_path: Path) -> None:
    db = tmp_path / "companion.sqlite"
    store = Store(db)
    store.append_utterance(utterance(rel=RelationshipId("a"), uid="u1"))
    store.append_utterance(utterance(rel=RelationshipId("b"), uid="u2"))
    store.close()
    with pytest.raises(SystemExit, match="several relationships"):
        resolve_relationship(None, db)
