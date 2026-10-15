from __future__ import annotations

from pathlib import Path

import pytest

from companion.cli.target import resolve_db, resolve_relationship


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


def test_relationship_defaults_to_the_file_name() -> None:
    assert (
        resolve_relationship(None, Path("data/telegram-8562130357.sqlite")) == "telegram-8562130357"
    )
    assert resolve_relationship("other", Path("data/x.sqlite")) == "other"
