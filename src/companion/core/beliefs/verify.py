"""The quote gate. A belief may only rest on words that appear in the source utterance."""

from __future__ import annotations

import re

from companion.core.types import Evidence, Utterance


class QuoteNotFoundError(ValueError):
    """The candidate quote does not occur in the source utterance."""


def _pattern(quote: str) -> re.Pattern[str] | None:
    words = quote.split()
    if not words:
        return None
    return re.compile(r"\s+".join(re.escape(w) for w in words), re.IGNORECASE)


def evidence_from(utterance: Utterance, quote: str) -> Evidence:
    """Return Evidence whose quote is an exact substring of the utterance text.

    Matching ignores case and whitespace runs, but the stored quote is the original slice,
    so the store can check it with a plain substring test.
    """
    pattern = _pattern(quote)
    match = pattern.search(utterance.text) if pattern else None
    if match is None:
        msg = f"quote not found in utterance {utterance.id}: {quote!r}"
        raise QuoteNotFoundError(msg)
    return Evidence(utterance_id=utterance.id, quote=match.group(0))
