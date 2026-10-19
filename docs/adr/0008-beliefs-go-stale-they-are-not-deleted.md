# 0008. Beliefs go stale; they are not deleted

**Status:** accepted 2026-10-15.

## Decision

How long a belief is worth asserting depends on its kind, and is measured from the freshest thing
the user said that supports it. Nothing is deleted or edited.

**Horizons** (`core/freshness.py`):

| Kind | Horizon |
|---|---|
| trait, preference, boundary, tell | 365 days |
| thread, promise | 30 days |
| state | 14 days |
| event | never (it is history) |

A belief is fresh until half its horizon, aging until the horizon, and stale after it.

**The card** (`core/card.py`):

- prints each belief with a relative age ("mentioned 3 weeks ago");
- adds "may have changed" to aging ones;
- moves stale ones out of the main block;
- puts up to three stale ordinary beliefs (`MAX_OLDER`) in a separate block marked as possibly out
  of date, so the companion can check naturally;
- leaves stale sensitive beliefs out entirely, because raising an old sensitive state is worse
  than missing it.

Every placement is a logged decision, with the reason.

**Restating refreshes.** The extractor sees recorded beliefs with short labels and may mark a
candidate as confirming one. Code verifies the quote like any other and attaches it as extra
evidence (`belief_evidence` stays insert-only, and its triggers still check quote, speaker and
frame). The belief's age then follows the new evidence.

## Why

- A card that asserts "has been lonely" in three months exactly as it does today is the confident
  staleness users describe as a companion that does not know what time it is.
- The clock line carries no date, so the old "(told you Oct 15)" gave the model nothing to reason
  with. A relative age does.
- Deleting is wrong here. A stale belief is still evidence of what was true, and the ledger and
  replay need it (ADR 0002). Not asserting it is enough.

## Consequences

- **The horizons are guesses,** borrowed from the constants other projects use (a week for episodic
  things, months for facts). They are written in one table so they can be tuned.
- Kind matters a lot, and the model assigns kind. A measurement filed as a `state` ages in two
  weeks. That is a prompt problem, not a freshness one.
- Confirmation is as good as the model's matching. A wrong label attaches evidence to the wrong
  belief. The quote and speaker gates stop fabricated or misattributed evidence, not a mismatched
  claim.
- Confidence is not yet derived from the number of independent days of evidence. That is the
  design's "assertable" threshold and is still to do.
- Related, from ADR 0010: beliefs from a non-real frame, or said as a joke or in pretend, are
  recorded but never shown as facts, whatever their age.

## Reverses if

Use shows the horizons cause wrong behaviour, for example asking about something that was never
stale or ignoring something that was. The table changes, not the mechanism.
