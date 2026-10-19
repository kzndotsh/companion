from __future__ import annotations

from pathlib import Path

import pytest

from companion import guidelines
from companion.guidelines import GuidelinesError, load, parse, with_guidelines


def test_the_default_routes_nothing_and_adds_no_text(tmp_path: Path) -> None:
    rules = load("default", tmp_path)
    assert (rules.route_intimate, rules.text, rules.version) == (False, "", "v1")
    assert with_guidelines("persona", rules) == "persona"


def test_a_private_file_wins_and_its_text_goes_under_its_heading(tmp_path: Path) -> None:
    (tmp_path / "default.md").write_text(
        "+++\nroute_intimate = true\n+++\nKeep it grown-up.\n", encoding="utf-8"
    )
    rules = load("default", tmp_path)
    assert (rules.route_intimate, rules.version) == (True, "local")
    assert (
        with_guidelines("persona", rules)
        == "persona\n\n## Operator guidelines\n\nKeep it grown-up.\n"
    )


@pytest.mark.parametrize(
    "raw",
    [
        "no settings block",
        "+++\nroute_intimate = 'yes'\n+++\n",
        "+++\nfloor = false\n+++\n",
        "+++\nroute_intimate = \n+++\n",
    ],
)
def test_a_bad_file_is_refused_in_plain_words(raw: str) -> None:
    with pytest.raises(GuidelinesError):
        parse(raw, "x", "local")


def test_there_is_no_setting_for_the_floor() -> None:
    with pytest.raises(GuidelinesError, match="the only setting is route_intimate"):
        parse("+++\nroute_intimate = true\nage_floor = false\n+++\n", "x", "local")


def test_unset_means_the_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(guidelines.GUIDELINES_ENV, raising=False)
    assert guidelines.chosen(tmp_path).id == "default"
