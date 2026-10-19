"""A character: a sheet of who the companion plays, laid on top of the persona.

The persona says how the companion behaves with anyone. A character sheet says who it is: name,
age, look, voice, tastes, quirks and an authored past. The sheet goes after the persona in the
same cached system block, under a fixed frame (`system/character-frame`) that says what the sheet
may override (voice, taste, identity, its own past) and what it may not (honesty that it is an AI
when sincerely asked, memory of them, closeness, limits and real danger).

A sheet is plain prompt text: whatever it says about the character, its age included, is read as
written.

Public sheets are versioned prompts at `prompts/characters/<id>/vN.md` (ADR 0013). Private sheets
live at `data/characters/<id>.md`, are never committed, and win over a public sheet of the same id.
`COMPANION_CHARACTER=<id>` picks one; unset means no character. A sheet may end with an
`## In scenes and intimate moments` section, which only the scene talker sees.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from companion import prompts

CHARACTER_ENV = "COMPANION_CHARACTER"
PRIVATE_DIR = Path("data/characters")
_ID = re.compile(r"[a-z0-9][a-z0-9-]*")
SCENE_HEADING = "\n## In scenes and intimate moments\n"


class CharacterError(ValueError):
    """A character that cannot be loaded, with the reason in plain words."""


@dataclass(frozen=True, slots=True)
class Character:
    id: str
    version: str  # "vN" for a public sheet, "local" for a private one
    sheet: str
    scene_sheet: str = (
        ""  # after an "## In scenes and intimate moments" heading: for the scene talker only
    )

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"


def parse(text: str, char_id: str, version: str) -> Character:
    """A sheet from its file text. Refuses an empty one."""
    sheet, _, scene = text.strip().partition(SCENE_HEADING)
    if not sheet.strip():
        msg = f"character {char_id!r} has an empty sheet"
        raise CharacterError(msg)
    return Character(char_id, version, sheet.strip(), scene.strip())


def load(char_id: str, private_dir: Path = PRIVATE_DIR) -> Character:
    """The private sheet if there is one, otherwise the current public version."""
    if not _ID.fullmatch(char_id):
        msg = f"character id {char_id!r} must be lowercase letters, digits and dashes"
        raise CharacterError(msg)
    private = private_dir / f"{char_id}.md"
    if private.is_file():
        return parse(private.read_text(encoding="utf-8"), char_id, "local")
    try:
        prompt = prompts.get(f"characters/{char_id}")
    except KeyError as err:
        msg = f"no character {char_id!r}: not in {private_dir} and not in prompts/characters"
        raise CharacterError(msg) from err
    return parse(prompt.raw, char_id, prompt.version)


def chosen(private_dir: Path = PRIVATE_DIR) -> Character | None:
    """The character `COMPANION_CHARACTER` names, or None when it is unset or empty."""
    char_id = os.environ.get(CHARACTER_ENV, "").strip()
    return load(char_id, private_dir) if char_id else None


def system_prompt(persona: str, character: Character | None, *, scene: bool = False) -> str:
    """The persona, then the frame and the sheet. Without a character, the persona unchanged. The
    scene talker's prompt (`scene`) adds the scene addendum and the part of the sheet after
    SCENE_HEADING, which the everyday talker never sees (ADR 0017)."""
    parts = [persona.rstrip()]
    if character is not None:
        parts += [prompts.get("system/character-frame").text, character.sheet]
    if scene:
        parts.append(prompts.get("system/scene-intimate").text)
        if character is not None and character.scene_sheet:
            parts.append(character.scene_sheet)
    return "\n\n".join(parts) + "\n" if len(parts) > 1 else persona
