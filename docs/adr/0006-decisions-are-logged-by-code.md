# 0006. Decisions are logged by code, not explained by models

**Status:** accepted 2026-10-15. Since 2026-10-19 it is built: the acknowledgement, frame and
listening judges, and the initiative gate, all follow it.

## Decision

Any component that makes a choice (moment read, frame, surface or withhold a belief, initiate)
returns scores. Code applies the thresholds and caps, then writes `Decision.reason` itself from
what was recorded. A model never writes the reason for its own decision.

## Why

- Decision models (Jev, Clef, Perplexity, Liquid d1) return a distribution and no reason.
- A reason written by an LLM is a rationalisation, not an audit trail (Turpin et al. 2023).
- The decision-layer audit in `docs/research/2026-10-15_decision-layer-audit/` (local only) found
  no candidate that produces a faithful reason.

## Contract

`Decision.detail` carries:

- `scorer`: the model that scored it;
- `schema_hash` and `inputs_hash`;
- `scores`: every option's probability;
- `threshold`;
- `vetoes`: the code rules that overrode the model.

The reason is rendered from these, for example
`withheld: P(fits moment)=0.31 < 0.55; option "venting, not asking"`. Replay stores the response
and never calls the scorer again. Judge and extractor decisions also carry the prompt as
`name@version` (ADR 0013).

## Consequences

- Eligibility, caps, cooldowns and initiative curves live in code. Models supply probabilities
  only.
- A Claude model cannot be the replayable scorer, because the Messages API returns no logprobs and
  rejects non-default sampling parameters on recent models. Replayable deciders need an open-weight
  scorer or a stored response.
- ADR 0014 extends the rule: models label, and code chooses.

## Reverses if

A decision model ships faithful, verifiable rationales.
