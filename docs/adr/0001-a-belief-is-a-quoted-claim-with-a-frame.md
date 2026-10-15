# 0001. A belief is a quoted claim with a frame

**Status:** accepted 2026-10-15. Records a decision already built (commit 7d81009).

**Decision.** What the companion believes about a person is stored as a `Belief` row, never as a
free-text note. Every belief carries:

- the claim, and one or more `Evidence` rows: a verbatim quote and the utterance it came from;
- who said it (`speaker`) and in what `frame` (real, play, story, hypothetical, out of character);
- `provenance` (stated, inferred, joked, played, hypothetical, third party, companion said);
- `confidence` and `sensitivity`;
- two times: when it became true (`valid_from`, `valid_until`) and when it was recorded
  (`recorded_at`), so a belief can be superseded without losing what was believed before.

The invariants are enforced twice, in the Python constructor and again as database constraints and
triggers, so a raw writer cannot bypass them:

- a claim needs at least one quote, and the quote must be an exact substring of the source
  utterance (`core/beliefs/verify.py` and the `evidence_quote_is_verbatim` trigger);
- provenance `companion_said` holds exactly when the speaker is the companion, so the companion's
  own words can never become a fact about the user;
- a play, story or hypothetical frame cannot carry sincere provenance (stated, inferred);
- evidence must match the belief's speaker and frame;
- a belief's claim and origin never change. It is closed or superseded, and a closed belief cannot
  be reopened.

The model proposes beliefs. Code decides which become rows. The speaker and frame come from the
source utterance, never from the model.

**Why.**
- A companion that remembers a joke, a game or a story as a fact about someone is the failure users
  notice most. Across 80 repositories audited on 2026-10-15, none had a frame field. The cheap
  fix is two columns and one gate.
- A made-up memory is worse than no memory. Requiring a verbatim quote makes fabricated recall
  structurally impossible: the quote exists in the ledger or the belief does not.
- Supersession is the best-solved piece of the field (bitemporal edges, refusal rules), so this is
  an integration choice, not research.

**Consequences.**
- Rejections are logged, not silently dropped. The slow loop writes a decision for every candidate
  it refuses, with the reason.
- Frame is currently always `real`, because nothing classifies frames yet. Until something does, the
  provenance label (joked, played, hypothetical) carries the signal.
- The gate proves a quote is real, not that the claim is right. A claim can match its quote and
  still misread it ("i'm so bad at getting distracted" was once stored as "bad at getting
  distracted"). Meaning needs other checks: prompt rules, review, and tests.
- Confidence is capped at 0.6 for a belief with a single piece of evidence.

**Reverses if.** A model can be shown to extract quoted, correctly framed beliefs more reliably than
code can check them. Even then the quote gate stays, because it is cheap and exact.
