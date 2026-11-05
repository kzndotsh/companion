from __future__ import annotations

import pytest

from companion.cli.main import GROUPS, HANDLERS, _parser  # pyright: ignore[reportPrivateUsage]


def test_every_command_is_under_exactly_one_heading() -> None:
    listed = [name for _, names in GROUPS for name in names]
    assert sorted(listed) == sorted(HANDLERS)
    assert len(listed) == len(set(listed))


def test_the_help_lists_one_command_per_line(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _parser().parse_args(["--help"])
    out = capsys.readouterr().out
    assert "{" not in out
    for name in HANDLERS:
        assert any(line.startswith(f"  {name} ") for line in out.splitlines()), name
