"""What the bot prints when it starts: what is running, from the same values it is configured
with."""

from __future__ import annotations

from companion import prompts
from companion.characters import Character
from companion.core import switch as sw
from companion.settings import Settings


def startup_lines(
    name: str,
    prefix_sha: str,
    character: Character | None = None,
    settings: Settings | None = None,
) -> list[str]:
    """What is running, a heading and one labelled row each for the prompts, the models, the limits
    and the switches by where they stand, printed from the same values the bot is configured
    with."""
    s = settings or Settings.from_env()
    judges = s.judge_model
    routed = ", ".join(f"{k} on {v}" for k, v in s.judge_routes.items())
    states = s.states()
    rows = [
        (
            "prompts",
            [
                f"persona {prompts.get('system/persona').version} (prefix {prefix_sha[:12]})",
                f"character {character.ref if character else 'none'}",
                f"set {prompts.set_hash()}",
            ],
        ),
        ("everyday", [s.everyday_model, f"standby {s.everyday_standby or 'none'}"]),
        ("roleplay", [s.roleplay_model or "the everyday model"]),
        ("judges", [judges + (f" ({routed})" if routed else "")]),
        ("limits", [f"daily cap {s.cap_text}", f"pace {s.pace}"]),
        ("live", states["live"]),
        ("shadow", states["shadow"]),
        ("off", states["off"]),
        ("dials", s.dials()),
    ]
    return [f"up as {name} on {s.value(sw.PLATFORM)}"] + [
        line for label, items in rows for line in _row(label, items)
    ]


def _row(label: str, items: list[str], width: int = 100) -> list[str]:
    """One labelled row, its items joined by commas and wrapped under the first."""
    lead = f"  {label:<9}"
    lines: list[str] = []
    line = lead
    for item in items or ["none"]:
        piece = item if line == lead else f", {item}"
        if line != lead and len(line) + len(piece) > width:
            lines.append(line + ",")
            line = " " * len(lead) + item
        else:
            line += piece
    return [*lines, line]
