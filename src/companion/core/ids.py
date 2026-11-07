"""Fresh ids: one place makes them, so a test can find every raw uuid."""

from __future__ import annotations

import uuid


def new_id() -> str:
    """A fresh id for a turn, a trace, a pass or a row."""
    return uuid.uuid4().hex
