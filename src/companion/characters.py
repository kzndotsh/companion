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
`## In roleplay and intimate moments` section, which only the roleplay talker sees, and that section
may end with a `## Scene reminder`: a few lines sent after the history on roleplay turns, where
models weight them most (2026-10-20: much more vivid scene replies than the same words at the top).
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
ROLEPLAY_HEADING = "\n## In roleplay and intimate moments\n"
# The heading as people write it: with or without the "##", a colon, any case. A sheet edited by
# hand once lost its "##", and the whole section reached the everyday talker unnoticed.
_ROLEPLAY_LINE = re.compile(
    r"^[ \t]*(?:#+[ \t]*)?in roleplay and intimate moments:?[ \t]*$", re.IGNORECASE | re.MULTILINE
)


_REMINDER_LINE = re.compile(
    r"^[ \t]*(?:#+[ \t]*)?scene reminder:?[ \t]*$", re.IGNORECASE | re.MULTILINE
)


class CharacterError(ValueError):
    """A character that cannot be loaded, with the reason in plain words."""


@dataclass(frozen=True, slots=True)
class Character:
    id: str
    version: str  # "vN" for a public sheet, "local" for a private one
    sheet: str
    roleplay_sheet: str = (
        ""  # after an "## In roleplay and intimate moments" heading: for the roleplay talker only
    )
    scene_reminder: str = (
        ""  # after a "## Scene reminder" heading: sent after the history in scenes
    )

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"


def parse(text: str, char_id: str, version: str) -> Character:
    """A sheet from its file text. Refuses an empty one."""
    text = text.strip()
    heading = _ROLEPLAY_LINE.search(text)
    sheet, scene = (text[: heading.start()], text[heading.end() :]) if heading else (text, "")
    if not sheet.strip():
        msg = f"character {char_id!r} has an empty sheet"
        raise CharacterError(msg)
    tail = _REMINDER_LINE.search(scene)
    scene, reminder = (scene[: tail.start()], scene[tail.end() :]) if tail else (scene, "")
    return Character(char_id, version, sheet.strip(), scene.strip(), reminder.strip())


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


def system_prompt(persona: str, character: Character | None, *, roleplay: bool = False) -> str:
    """The persona, then the frame and the sheet. Without a character, the persona unchanged. The
    roleplay talker's prompt (`roleplay`) adds the part of the sheet after ROLEPLAY_HEADING, which
    the everyday talker never sees (ADR 0017)."""
    parts = [persona.rstrip()]
    if character is not None:
        parts += [prompts.get("system/character-frame").text, character.sheet]
    if roleplay and character is not None and character.roleplay_sheet:
        parts.append(character.roleplay_sheet)
    return "\n\n".join(parts) + "\n" if len(parts) > 1 else persona
