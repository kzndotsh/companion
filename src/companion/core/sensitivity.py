"""Where the sensitivity levels draw a line. One name per rule, so a rule changes in one place."""

from __future__ import annotations

from companion.core.types import Sensitivity

# A memory at this level or above is guarded: never brought up on its own (a thought, a plan, a
# date, a guess), never closed by code, and shown on the card only while they are sharing. The
# owner's rule for "too sensitive to surface unprompted".
GUARDED_AT = Sensitivity.DELICATE
