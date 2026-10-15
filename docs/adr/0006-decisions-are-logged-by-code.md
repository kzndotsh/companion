# 0006. Decisions are logged by code, not explained by models

**Status:** accepted 2026-10-15. Nothing implements it yet; it binds the first decider.

**Decision.** Any component that makes a choice (moment read, frame, surface or withhold a belief, initiate) returns scores. Code applies the thresholds and caps, then writes `Decision.reason` itself from what was recorded. A model never writes the reason for its own decision.

**Why.** Decision models (Jev, Clef, Perplexity, Liquid d1) return a distribution and no reason. A reason written by an LLM is a rationalisation, not an audit trail (Turpin et al. 2023). The decision-layer audit in `docs/research/2026-10-15_decision-layer-audit/` found no candidate that produces a faithful reason.

**Contract.** `Decision.detail` carries `scorer` (id and version), `schema_hash`, `inputs_hash`, `scores` (every option's probability), `threshold`, and `vetoes` (the code rules that overrode the model). The reason is rendered from these, for example `withheld: P(fits moment)=0.31 < 0.55; option "venting, not asking"`. Replay stores the response and never calls the scorer again.

**Consequences.** Eligibility, caps, cooldowns and initiative curves live in code. Models supply probabilities only. A Claude model cannot be the replayable scorer, because the Messages API returns no logprobs and rejects non-default sampling parameters on recent models. Replayable deciders need an open-weight scorer or a stored response.

**Reverses if.** A decision model ships faithful, verifiable rationales.
