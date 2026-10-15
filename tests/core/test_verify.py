from __future__ import annotations

from collections.abc import Callable

import pytest

from companion.core.beliefs.verify import QuoteNotFoundError, evidence_from
from companion.core.types import Utterance


def test_returns_the_original_slice_not_the_candidate(utterance: Callable[..., Utterance]) -> None:
    u = utterance("My studio has  never been CLEANER, which is how I know")
    e = evidence_from(u, "my studio has never been cleaner")
    assert e.quote == "My studio has  never been CLEANER"
    assert e.quote in u.text


def test_rejects_words_that_were_not_said(utterance: Callable[..., Utterance]) -> None:
    u = utterance("I applied for the fellowship")
    with pytest.raises(QuoteNotFoundError):
        evidence_from(u, "she drives past her old office")


def test_rejects_a_quote_that_is_only_whitespace(utterance: Callable[..., Utterance]) -> None:
    with pytest.raises(QuoteNotFoundError):
        evidence_from(utterance("hello"), "   ")
