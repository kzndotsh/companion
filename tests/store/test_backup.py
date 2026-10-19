from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import pytest

from companion import backups
from companion.core.types import Utterance
from companion.store.sqlite.backup import BackupError, check, prune, restore, snapshot, snapshots
from companion.store.sqlite.store import Store
from tests.conftest import T0


def _db(tmp_path: Path, utterance: Callable[..., Utterance], n: int = 2) -> Path:
    path = tmp_path / "data" / "rel.sqlite"
    path.parent.mkdir(exist_ok=True)
    store = Store(path)
    for _ in range(n):
        store.append_utterance(utterance())
    store.close()
    return path


def test_a_snapshot_is_checked_and_counts_the_messages(
    tmp_path: Path, utterance: Callable[..., Utterance]
) -> None:
    db = _db(tmp_path, utterance)
    copy, n = snapshot(db, tmp_path / "b", "start", T0)
    assert n == 2
    assert copy.name.endswith("-start.sqlite")
    assert check(copy) == 2
    assert sorted(p.name for p in (tmp_path / "b").iterdir()) == [copy.name]  # one file, no -wal


def test_a_corrupt_database_leaves_no_snapshot(tmp_path: Path) -> None:
    bad = tmp_path / "rel.sqlite"
    bad.write_bytes(b"not a database at all" * 100)
    with pytest.raises(BackupError):
        snapshot(bad, tmp_path / "b", "start", T0)
    assert list((tmp_path / "b").iterdir()) == []


def test_daily_and_other_snapshots_are_kept_apart(
    tmp_path: Path, utterance: Callable[..., Utterance]
) -> None:
    db, into = _db(tmp_path, utterance), tmp_path / "b"
    for i in range(4):
        snapshot(db, into, "daily", T0 + timedelta(days=i))
    for i in range(5):
        snapshot(db, into, "start", T0 + timedelta(days=9, minutes=i))
    prune(into, "rel", 2, daily=False)
    names = [p.name for p in snapshots(into, "rel")]
    assert sum(n.endswith("-daily.sqlite") for n in names) == 4  # restarts never push these out
    assert sum(n.endswith("-start.sqlite") for n in names) == 2


def test_a_bad_backup_never_touches_the_live_database(
    tmp_path: Path, utterance: Callable[..., Utterance]
) -> None:
    db = _db(tmp_path, utterance)
    bad = tmp_path / "bad.sqlite"
    bad.write_bytes(b"garbage" * 500)
    with pytest.raises(BackupError):
        restore(bad, db, tmp_path / "b", T0)
    assert check(db) == 2


def test_a_restore_puts_the_snapshot_back_and_keeps_what_was_there(
    tmp_path: Path, utterance: Callable[..., Utterance]
) -> None:
    db = _db(tmp_path, utterance)
    old, _ = snapshot(db, tmp_path / "b", "manual", T0)
    store = Store(db)
    store.append_utterance(utterance())  # a third message, after the snapshot
    store.close()
    kept = restore(old, db, tmp_path / "b", T0 + timedelta(hours=1))
    assert check(db) == 2
    assert check(kept) == 3  # the database before the restore is kept


def test_backing_up_copies_the_character_sheets_and_skips_the_env(
    tmp_path: Path, utterance: Callable[..., Utterance], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("COMPANION_BACKUP_DIR", raising=False)
    db = _db(tmp_path, utterance)
    (db.parent / "characters").mkdir()
    (db.parent / "characters" / "sam.md").write_text("a sheet")
    said = backups.back_up(db.parent, db, "manual", T0)
    into = db.parent / "backups"
    assert "backed up 2 messages" in said
    assert [p.name for p in into.glob("characters-*/sam.md")] == ["sam.md"]
    assert not list(into.rglob(".env"))
