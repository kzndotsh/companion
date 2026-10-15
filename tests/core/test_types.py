from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import pytest

from companion.core.types import Belief, BeliefId, Frame, Provenance, Speaker
from tests.conftest import T0


def test_companion_words_cannot_become_sincere_facts(belief: Callable[..., Belief]) -> None:
    with pytest.raises(ValueError, match="companion_said"):
        belief(speaker=Speaker.COMPANION, provenance=Provenance.STATED)


def test_users_words_cannot_be_tagged_as_the_companions(belief: Callable[..., Belief]) -> None:
    with pytest.raises(ValueError, match="companion_said"):
        belief(speaker=Speaker.USER, provenance=Provenance.COMPANION_SAID)


@pytest.mark.parametrize("frame", [Frame.PLAY, Frame.STORY, Frame.HYPOTHETICAL])
@pytest.mark.parametrize("provenance", [Provenance.STATED, Provenance.INFERRED])
def test_non_real_frames_cannot_carry_sincere_provenance(
    belief: Callable[..., Belief], frame: Frame, provenance: Provenance
) -> None:
    with pytest.raises(ValueError, match="sincere"):
        belief(frame=frame, provenance=provenance)


def test_a_played_statement_is_representable_as_played(belief: Callable[..., Belief]) -> None:
    b = belief(frame=Frame.PLAY, provenance=Provenance.PLAYED)
    assert b.provenance is Provenance.PLAYED


def test_ooc_corrections_can_be_stated(belief: Callable[..., Belief]) -> None:
    assert belief(frame=Frame.OOC, provenance=Provenance.STATED).frame is Frame.OOC


def test_a_belief_needs_evidence(belief: Callable[..., Belief]) -> None:
    with pytest.raises(ValueError, match="verified quote"):
        belief(evidence=())


def test_superseded_belief_must_be_closed(belief: Callable[..., Belief]) -> None:
    with pytest.raises(ValueError, match="closed"):
        belief(superseded_by=BeliefId("b2"))


def test_validity_cannot_run_backwards(belief: Callable[..., Belief]) -> None:
    with pytest.raises(ValueError, match="precedes"):
        belief(valid_until=T0 - timedelta(days=1))


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_confidence_is_bounded(belief: Callable[..., Belief], confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        belief(confidence=confidence)
