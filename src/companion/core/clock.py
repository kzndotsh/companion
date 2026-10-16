"""The line that tells the companion the time. It rides the system block, not a user message."""

from __future__ import annotations

from datetime import datetime, timedelta

QUIET_GAP = timedelta(minutes=1)


def describe_gap(gap: timedelta) -> str | None:
    """None when the conversation is effectively continuous."""
    if gap < QUIET_GAP:
        return None
    minutes = int(gap.total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    days = hours // 24
    if days < 14:
        return f"{days} day{'s' if days != 1 else ''}"
    weeks = days // 7
    return f"{weeks} weeks"


def now_line(now: datetime, previous: datetime | None) -> str:
    """`now` is shown in the machine's local zone; `previous` is the last message before it."""
    stamp = now.astimezone().strftime("%A %H:%M")
    gap = describe_gap(now - previous) if previous is not None else None
    if gap:
        return f"Right now it is {stamp}. Their last message came {gap} ago."
    return f"Right now it is {stamp}."
