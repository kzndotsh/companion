"""The system block in tagged sections (measured 2026-10-19, `evals/CHANGELOG.md`).

The clock and the turn's notes go in `<clock>` and `<notes>`; on the everyday talker that read the
clock right at night (12 of 12 against 9) and acted on a due plan more often (12 against 8), with no
tag copied into a reply. The memory blocks stay as bracketed text: tagged too, the model all but
stopped making small callbacks to what it knows, which the owner prefers it keeps. The words inside
every part are unchanged.
"""

from __future__ import annotations

import re

from companion.core.card import GUARDED_HEADING, MEMORY_HEADING, OLDER_HEADING, VIEWS_HEADING
from companion.prompts import get

_BRACKETED = re.compile(r"\[(.*?)\]", re.DOTALL)
# The blocks that are memory, not notes, found by their opening words: the card's own, and the
# scene card's blocks (ADR 0026) by their notes' own opening words.
_MEMORY_HEADINGS = (
    MEMORY_HEADING,
    GUARDED_HEADING,
    OLDER_HEADING,
    VIEWS_HEADING,
    *(
        get(f"notes/scene-{part}").text.split("$")[0].lstrip("[")
        for part in ("limits", "known", "offer", "basics")
    ),
)


def tagged(card: str) -> str:
    """The same system block with the clock in a tag and every bracketed line that is not a memory
    block gathered under notes. The words inside are unchanged; the memory blocks stay bracketed as
    the turn sends them."""
    parts: list[str] = []
    notes: list[str] = []
    rest = card
    for m in _BRACKETED.finditer(card):
        body = m.group(1).strip()
        if body.startswith(_MEMORY_HEADINGS):
            parts.append(m.group(0))
        else:
            notes.append(body)
        rest = rest.replace(m.group(0), "", 1)
    plain = [line.strip() for line in rest.splitlines() if line.strip()]
    clock = [f"<clock>{line}</clock>" for line in plain]
    notes_block = ["<notes>\n" + "\n".join(notes) + "\n</notes>"] if notes else []
    return "\n".join([*clock, *parts, *notes_block])
