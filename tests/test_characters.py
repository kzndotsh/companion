from __future__ import annotations

from pathlib import Path

import pytest

from companion import characters
from companion.characters import CharacterError, load, parse, system_prompt
from companion.evals.variants import parse_spec

SHEET = "You are Mika, 19. Bubbly, loves indie music and small dogs.\n"


def test_a_sheet_is_its_text_and_an_empty_one_is_refused() -> None:
    mika = parse(SHEET, "mika", "local")
    assert (mika.ref, mika.sheet) == ("mika@local", SHEET.strip())
    with pytest.raises(CharacterError, match="empty sheet"):
        parse("\n  \n", "mika", "local")


def test_a_private_sheet_is_loaded_and_an_unknown_one_is_refused(tmp_path: Path) -> None:
    (tmp_path / "mika.md").write_text(SHEET, encoding="utf-8")
    assert load("mika", tmp_path).version == "local"
    with pytest.raises(CharacterError, match="no character"):
        load("nobody", tmp_path)
    with pytest.raises(CharacterError, match="lowercase"):
        load("../etc", tmp_path)


def test_the_sheet_follows_the_persona_under_the_frame() -> None:
    built = system_prompt("PERSONA\n", parse(SHEET, "mika", "local"))
    assert built.index("PERSONA") < built.index("## Who you are") < built.index("You are Mika")
    assert "say so plainly" in built
    assert built.endswith("small dogs.\n")
    assert system_prompt("PERSONA\n", None) == "PERSONA\n"


def test_no_character_unless_the_setting_names_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(characters.CHARACTER_ENV, raising=False)
    assert characters.chosen(tmp_path) is None
    (tmp_path / "mika.md").write_text(SHEET, encoding="utf-8")
    monkeypatch.setenv(characters.CHARACTER_ENV, "mika")
    chosen = characters.chosen(tmp_path)
    assert chosen is not None
    assert chosen.ref == "mika@local"


def test_an_eval_variant_can_name_a_character() -> None:
    spec = parse_spec("v26.md+as-mika+roleplay")
    assert spec.character == "mika"
    assert spec.label == "v26.md+as-mika+roleplay"


def test_the_in_scenes_section_reaches_only_the_roleplay_talker() -> None:
    from companion.characters import system_prompt  # noqa: PLC0415

    char = parse(
        "You are Mika.\n\n## In roleplay and intimate moments\nStay in the role.\n", "mika", "local"
    )
    assert (char.sheet, char.roleplay_sheet) == ("You are Mika.", "Stay in the role.")
    everyday = system_prompt("persona", char)
    scene = system_prompt("persona", char, roleplay=True)
    assert "Stay in the role." not in everyday
    assert scene.endswith("Stay in the role.\n")
    assert system_prompt("persona", None) == "persona"


@pytest.mark.parametrize(
    "heading",
    [
        "## In roleplay and intimate moments",
        "In roleplay and intimate moments:",
        "# in roleplay and intimate moments",
    ],
)
def test_the_roleplay_section_is_cut_out_however_the_heading_is_written(heading: str) -> None:
    c = parse(f"You are Mika.\n\n{heading}\nStay in the role.\n", "mika", "local")
    assert c.sheet == "You are Mika."
    assert c.roleplay_sheet == "Stay in the role."


def test_a_scene_reminder_is_kept_apart_from_both_the_sheet_and_the_scene_section() -> None:
    c = parse(
        "You are Mika.\n\n## In roleplay and intimate moments\nWrite only your own actions.\n\n"
        "## Scene reminder\nBe specific.",
        "mika",
        "local",
    )
    assert c.roleplay_sheet == "Write only your own actions."
    assert c.scene_reminder == "Be specific."
    assert "Be specific." not in system_prompt("Persona.", c, roleplay=True)
    assert parse("You are Mika.", "mika", "local").scene_reminder == ""


def test_the_serious_section_is_kept_for_code_and_no_talker_sees_it() -> None:
    c = parse(
        "You are Mika.\n\n## When it is serious\nhey. reach $line, okay? i'm here.\n\n"
        "## In roleplay and intimate moments\nWrite only your own actions.\n\n"
        "## Scene reminder\nBe specific.",
        "mika",
        "local",
    )
    assert c.serious == "hey. reach $line, okay? i'm here."
    assert (c.sheet, c.roleplay_sheet, c.scene_reminder) == (
        "You are Mika.",
        "Write only your own actions.",
        "Be specific.",
    )
    assert "reach $line" not in system_prompt("Persona.", c, roleplay=True)
    assert parse("You are Mika.", "mika", "local").serious == ""


def test_the_serious_section_can_come_last() -> None:
    c = parse("You are Mika.\n\nwhen it is serious:\nstay. $line.", "mika", "local")
    assert (c.sheet, c.serious) == ("You are Mika.", "stay. $line.")
