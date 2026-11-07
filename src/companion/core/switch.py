"""The switches: every setting that turns a part of the bot on, shadows it or off, or picks one
value from a short list.

A switch is one `Switch` row here, and every use names the row itself, so a typo fails at import or
type-check time. A switch's position is a `Mode` when it takes on, shadow or off; a platform, a
dial or a routing choice keeps its own words. `settings.Settings` reads the rows from the
environment and the `Runtime` carries the modes, both keyed by the row. The rows sit in core, not
beside each feature, because core and the kit read them and may not import a feature or `settings`.
A new switch is one row here (and a row in `core/shadows.py` when it defaults to shadow), its place
in `SWITCHES` and its uses.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from companion.core.reachout import DEFAULT_DIAL, Dial


class Mode(StrEnum):
    """Where a switch stands: acting (`ON`), working and logging without showing (`SHADOW`), or not
    running (`OFF`)."""

    ON = "on"
    SHADOW = "shadow"
    OFF = "off"


OFF_WORDS = frozenset({"off", "0", "no", "false"})
ON_WORDS = frozenset({"on", "1", "yes", "true"})


@dataclass(frozen=True, slots=True, eq=False)
class Switch:
    """One row; compared by identity, so the row itself is the key."""

    env: str
    label: str  # its name on the startup block
    values: tuple[str, ...]  # the first is the default
    shown: Mapping[str, str] | None = None  # how a value reads on the startup block, when not as is

    def read(self, environ: Mapping[str, str]) -> str:
        """Unset is the default, and an on or off word on a switch without that position (on for one
        with no live mode) is its first one. Any other value it does not know stops the bot: a typo
        used to become the default without a word."""
        raw = environ.get(self.env, "").strip().lower()
        value = Mode.OFF if raw in OFF_WORDS else Mode.ON if raw in ON_WORDS else raw
        if value in self.values:
            return value
        if raw and value not in (Mode.ON, Mode.OFF):
            msg = f"{self.env}={raw!r} is not a value it knows: {', '.join(self.values)}"
            raise SystemExit(msg)
        return self.values[0]

    @property
    def is_mode(self) -> bool:
        """Whether every value it takes is a `Mode`."""
        return all(v in Mode for v in self.values)


PLATFORM = Switch(
    "COMPANION_PLATFORM", "platform", ("telegram", "discord")
)  # which chat it runs on
SPLIT = Switch("COMPANION_SPLIT", "split", (Mode.ON, Mode.OFF))
LISTEN = Switch("COMPANION_LISTEN", "listen", (Mode.ON, Mode.OFF))
INITIATIVE = Switch("COMPANION_INITIATIVE", "initiative", (Mode.SHADOW, Mode.OFF))
MOOD = Switch("COMPANION_MOOD", "mood", (Mode.ON, Mode.SHADOW, Mode.OFF))
REDRAW = Switch("COMPANION_REDRAW", "redraw", (Mode.ON, Mode.OFF))
ROUTE_INTIMATE = Switch(
    "COMPANION_ROUTE_INTIMATE",
    "intimate",
    (Mode.OFF, Mode.ON),
    {Mode.ON: "may route", Mode.OFF: "stays"},
)
RELEVANCE = Switch("COMPANION_RELEVANCE", "relevance", (Mode.ON, Mode.SHADOW, Mode.OFF))
REREAD = Switch("COMPANION_REREAD", "re-read", (Mode.ON, Mode.SHADOW, Mode.OFF))
PROMISES = Switch("COMPANION_PROMISES", "promises", (Mode.SHADOW, Mode.OFF))
LORE = Switch("COMPANION_LORE", "lore", (Mode.ON, Mode.SHADOW, Mode.OFF))
FOCUS = Switch("COMPANION_FOCUS", "focus", (Mode.ON, Mode.OFF))
REMINDERS = Switch("COMPANION_REMINDERS", "reminders", (Mode.ON, Mode.OFF))
EPISODES = Switch("COMPANION_EPISODES", "episodes", (Mode.ON, Mode.SHADOW, Mode.OFF))
OWN_MARKS = Switch("COMPANION_OWN_MARKS", "own marks", (Mode.ON, Mode.OFF))
HEDGED_PLANS = Switch(
    "COMPANION_HEDGED_PLANS", "hedged plans", ("loose", Mode.OFF), {Mode.OFF: "strict"}
)
REACH = Switch(
    "COMPANION_REACH",
    "reach",
    (DEFAULT_DIAL.value, *(d.value for d in Dial if d is not DEFAULT_DIAL)),
)
CRISIS = Switch("COMPANION_CRISIS", "crisis", (Mode.ON, Mode.SHADOW, Mode.OFF))
CALENDAR = Switch("COMPANION_CALENDAR", "calendar", (Mode.ON, Mode.OFF))
NOW = Switch("COMPANION_NOW", "now", (Mode.SHADOW, Mode.ON, Mode.OFF))
HISTORY = Switch("COMPANION_HISTORY", "history", (Mode.SHADOW, Mode.ON, Mode.OFF))
INTIMATE_MEMORY = Switch(
    "COMPANION_INTIMATE_MEMORY", "intimate memory", (Mode.ON, Mode.SHADOW, Mode.OFF)
)

# In the order they appear on the startup block, within its rows.
SWITCHES: tuple[Switch, ...] = (
    PLATFORM,
    SPLIT,
    LISTEN,
    INITIATIVE,
    MOOD,
    REDRAW,
    ROUTE_INTIMATE,
    RELEVANCE,
    REREAD,
    PROMISES,
    LORE,
    FOCUS,
    REMINDERS,
    EPISODES,
    OWN_MARKS,
    HEDGED_PLANS,
    REACH,
    CRISIS,
    CALENDAR,
    NOW,
    HISTORY,
    INTIMATE_MEMORY,
)
