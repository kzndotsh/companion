"""A note about how long to answer, from how long they wrote, never from the model.

On short, casual statements the replies ran three to four times longer than the message they
answered (a 4-word message got a median of 15 words; see `evals/CHANGELOG.md`). When they wrote a
lot, or asked something, the length was already about right, so the note only appears for a short
statement. It rides in the system block with the clock, never in their message.
"""

from __future__ import annotations

import math

MAX_USER_WORDS = 12
FLOOR_WORDS = 8


def reply_limit(user_words: int) -> int:
    """About one and a half times what they wrote, plus a little, never below a floor."""
    return max(FLOOR_WORDS, math.ceil(1.5 * user_words) + 4)


def length_note(user_text: str) -> str | None:
    """The note for a short statement, or None for a question, a long message or nothing."""
    words = len(user_text.split())
    if words == 0 or words > MAX_USER_WORDS or "?" in user_text:
        return None
    unit = "word" if words == 1 else "words"
    return (
        f"[Their message was short ({words} {unit}), so keep your reply short too, "
        f"under about {reply_limit(words)} words, unless what they said needs more.]"
    )
