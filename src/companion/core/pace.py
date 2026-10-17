"""How long a reply waits before it is sent, so it lands like a person typing, not instantly.

The model answers in about a second, which no one reading and typing could do. The wait is a pure
function of the two texts: a short pause to read what they sent, then time to type the reply, less
whatever the model already took. It is capped so a turn never feels broken. The pace setting
scales it: "off" sends at once. The io layer adds the random jitter and does the waiting; nothing
here reads a clock.
"""

from __future__ import annotations

PACES = {"off": 0.0, "quick": 0.5, "natural": 1.0, "slow": 1.6}
DEFAULT_PACE = "natural"
READ_BASE_SECONDS = 0.8
READ_PER_WORD = 0.03
READ_MAX_SECONDS = 2.0
TYPE_PER_WORD = 0.15
MAX_SECONDS = 8.0


def pace_factor(raw: str) -> float:
    """The factor for a setting name. Unset or unknown means the default."""
    return PACES.get(raw.strip().lower(), PACES[DEFAULT_PACE])


def target_seconds(user_text: str, reply_text: str, factor: float, jitter: float = 1.0) -> float:
    """The whole time from their message to the reply going out. An empty reply (a reaction)
    only pays the reading pause."""
    read = min(READ_BASE_SECONDS + READ_PER_WORD * len(user_text.split()), READ_MAX_SECONDS)
    typing = TYPE_PER_WORD * len(reply_text.split())
    return min((read + typing) * factor * jitter, MAX_SECONDS)


def hold_seconds(
    user_text: str, reply_text: str, factor: float, elapsed: float, jitter: float = 1.0
) -> float:
    """How much longer to wait, given the model has already taken `elapsed` seconds."""
    return max(0.0, target_seconds(user_text, reply_text, factor, jitter) - elapsed)
