from __future__ import annotations

import pytest

from companion.cli.main import COMMANDS, HANDLERS, _parser  # pyright: ignore[reportPrivateUsage]
from companion.kit.command import Group


def test_every_command_is_declared_once_under_one_heading() -> None:
    names = [c.name for c in COMMANDS]
    assert len(names) == len(set(names))
    assert sorted(names) == sorted(HANDLERS)
    assert all(isinstance(c.group, Group) for c in COMMANDS)


def test_the_help_lists_one_command_per_line(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _parser().parse_args(["--help"])
    out = capsys.readouterr().out
    assert "{" not in out
    for name in HANDLERS:
        assert any(line.startswith(f"  {name} ") for line in out.splitlines()), name


def test_no_help_line_says_whether_something_is_in_shadow(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Whether a feature runs in shadow changes at its review; `companion shadows` says it."""
    with pytest.raises(SystemExit):
        _parser().parse_args(["--help"])
    lines = capsys.readouterr().out.splitlines()
    assert not [ln for ln in lines if "shadow" in ln and not ln.startswith("  shadows ")]
