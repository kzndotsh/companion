"""The system block in tagged sections (measured 2026-10-19, `evals/CHANGELOG.md`).

The clock and the turn's notes go in `<clock>` and `<notes>`; on the everyday talker that read the
clock right at night (12 of 12 against 9) and acted on a due plan more often (12 against 8), with no
tag copied into a reply. The memory blocks stay as bracketed text: tagged too, the model all but
stopped making small callbacks to what it knows, which the owner prefers it keeps. The words inside
every part are unchanged.
"""

from __future__ import annotations

import re

_BRACKETED = re.compile(r"\[(.*?)\]", re.DOTALL)
_SECTIONS = (
    ("What you remember", "memory"),
    ("Also known", "held"),
    ("Older, and may be out of date", "older"),
    ("Views of your own", "views"),
)


def tagged(card: str, *, memory: bool = True) -> str:
    """The same system block with each part in a tag: the clock, each memory block, and every
    other bracketed line gathered under notes. The words inside are unchanged (`+tags`). With
    `memory` off the memory blocks stay bracketed as they are (`+tagsnotes`)."""
    parts: list[str] = []
    notes: list[str] = []
    rest = card
    for m in _BRACKETED.finditer(card):
        body = m.group(1).strip()
        tag = next((t for head, t in _SECTIONS if body.startswith(head)), None)
        if tag is None:
            notes.append(body)
        elif memory:
            parts.append(f"<{tag}>\n{body}\n</{tag}>")
        else:
            parts.append(m.group(0))
        rest = rest.replace(m.group(0), "", 1)
    plain = [line.strip() for line in rest.splitlines() if line.strip()]
    clock = [f"<clock>{line}</clock>" for line in plain]
    notes_block = ["<notes>\n" + "\n".join(notes) + "\n</notes>"] if notes else []
    return "\n".join([*clock, *parts, *notes_block])
