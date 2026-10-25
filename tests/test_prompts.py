from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

import pytest

from companion import prompts

ROOT = Path(str(resources.files("companion.prompts")))
PLACEHOLDERS = {
    "notes/length": {"words", "unit", "limit"},
    "notes/length-serious": {"limit"},
    "notes/recall": {"items"},
    "notes/relevant": {"items"},
    "notes/own-mark": {"mark"},
    "notes/own-mark-theirs": {"mark", "theirs"},
    "notes/recent-times": {"items"},
    "notes/lore": {"items"},
    "notes/listening-trivial": {"examples"},
    "notes/topic-spent": {"move"},
    "notes/guess": {"about", "items"},
    "notes/loop-follow-up": {"claim"},
    "notes/loop-celebrate": {"claim"},
    "notes/loop-encourage": {"claim"},
    "notes/habit-opener": {"n", "total", "word"},
    "notes/habit-phrases": {"phrases"},
    "notes/habit-moves": {"habits"},
    "notes/clock": {"stamp"},
    "notes/address": {"address"},
    "notes/clock-gap": {"gap"},
    "notes/reminder-set": {"what", "when", "extra"},
    "notes/reminder-ask": {"what", "reason"},
    "notes/reminder-cancelled": {"what"},
    "notes/occasion-day": {"name"},
    "notes/occasion-soon": {"name", "when"},
    "notes/occasion-us": {"span"},
    "system/reminder-send": {"what"},
    "notes/crisis-concern": {"line"},
    "messages/crisis-line": {"line"},
}
# a prompt that gained its placeholders in a later version: earlier versions have none
SINCE = {"notes/listening-trivial": 6}


def _all_versions() -> dict[str, list[str]]:
    return {name: prompts.versions(name) for name in prompts.manifest()}


def test_every_manifest_entry_names_a_version_that_exists() -> None:
    for name, version in prompts.manifest().items():
        assert version in prompts.versions(name), f"{name} is pinned to a missing {version}"


def test_every_prompt_folder_is_in_the_manifest() -> None:
    folders = {
        str(p.parent.relative_to(ROOT))
        for p in ROOT.rglob("v*.md")
        if re.fullmatch(r"v\d+\.md", p.name)
    }
    assert folders == set(prompts.manifest()), "a prompt folder is missing from manifest.toml"


def test_every_version_has_a_changelog_entry_and_every_entry_has_a_file() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    entries = set(re.findall(r"^- \*\*(\S+) (v\d+)\*\*", changelog, re.MULTILINE))
    files = {(name, v) for name, vs in _all_versions().items() for v in vs}
    assert files - entries == set(), "a version file has no entry in prompts/CHANGELOG.md"
    assert entries - files == set(), "a changelog entry has no file"


def test_files_end_in_one_newline_and_have_no_trailing_spaces_or_carriage_returns() -> None:
    for name in prompts.manifest():
        for version in prompts.versions(name):
            raw = (ROOT / name / f"{version}.md").read_text(encoding="utf-8")
            assert raw.endswith("\n"), f"{name} {version} does not end with a newline"
            assert not raw.endswith("\n\n"), f"{name} {version} ends with a blank line"
            assert "\r" not in raw
            for line in raw.splitlines():
                assert line == line.rstrip(), f"{name} {version} has trailing whitespace"


def test_placeholders_are_exactly_the_ones_the_code_fills_in() -> None:
    for name in prompts.manifest():
        for version in prompts.versions(name):
            early = int(version.removeprefix("v")) < SINCE.get(name, 0)
            wanted: set[str] = set() if early else PLACEHOLDERS.get(name, set())
            assert prompts.get(name, version).placeholders == wanted, f"{name} {version}"


def test_render_fills_every_placeholder_and_refuses_a_missing_one() -> None:
    clock = prompts.get("notes/clock")
    assert clock.render(stamp="Friday 02:15") == "Right now it is Friday 02:15."
    with pytest.raises(KeyError):
        clock.render()


def test_a_prompt_has_a_name_a_version_a_ref_and_a_stable_hash() -> None:
    p = prompts.get("system/ack")
    assert p.ref == f"system/ack@{prompts.manifest()['system/ack']}"
    assert p.sha == prompts.get("system/ack").sha
    assert len(p.sha) == 12


def test_an_unknown_prompt_or_version_is_an_error() -> None:
    with pytest.raises(KeyError):
        prompts.get("system/nope")
    with pytest.raises(KeyError):
        prompts.get("system/ack", "v999")


def test_overrides_pick_another_version_and_unknown_names_are_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    older = prompts.versions("system/ack")[0]
    before = prompts.set_hash()
    monkeypatch.setenv(prompts.OVERRIDES_ENV, f"system/ack={older}")
    assert prompts.get("system/ack").version == older
    assert prompts.set_hash() != before
    monkeypatch.setenv(prompts.OVERRIDES_ENV, "system/nothing=v1")
    with pytest.raises(KeyError):
        prompts.manifest()


def test_versions_are_listed_in_numeric_order() -> None:
    assert prompts.versions("system/extract") == [f"v{n}" for n in range(1, 10)]


def test_the_readme_lists_every_prompt_at_its_current_version() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    listed = dict(re.findall(r"^\| `([^`]+)` \|.*\| (v\d+) \|$", readme, re.MULTILINE))
    assert listed == prompts.manifest(), "prompts/README.md is out of step with manifest.toml"


def test_a_note_is_one_bracketed_line_except_the_clock_and_the_listening_parts() -> None:
    """The clock stays a plain sentence: bracketed, the model copied it into replies (persona v17
    in CHANGELOG.md). Listening notes are parts that `listening_note` joins and brackets as one."""
    for prompt in prompts.current():
        if not prompt.name.startswith("notes/"):
            continue
        bracketed = prompt.text.startswith("[") and prompt.text.endswith("]")
        plain = prompt.name.startswith(
            ("notes/clock", "notes/listening-", "notes/topic-move-", "notes/trivial-reactions")
        )
        assert bracketed != plain, f"{prompt.ref} should {'not ' if plain else ''}be in [brackets]"


def test_a_listening_note_reaches_the_model_bracketed() -> None:
    from companion.core.turn.listening import Judgement, listening_note  # noqa: PLC0415

    for severity in (0, 1, 2):
        for vague in (False, True):
            j = Judgement(severity, "listening", vague, medical=severity == 2, rude=False)
            note = listening_note(j, [])
            assert note is None or (note.startswith("[") and note.endswith("]")), note
