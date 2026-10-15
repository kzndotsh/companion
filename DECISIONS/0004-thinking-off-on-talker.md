# 0004. The talker never reasons

**Status:** accepted 2026-10-15.

**Decision.** The fast loop's talker is called with thinking disabled. `TalkerRequest` has no thinking field, so a caller cannot ask for it. Reasoning belongs to the slow loop's thinker.

**Why.** Every current fast tier reasons by default. Measured in the speed audit: Haiku 5.5 first answer token is 7.7 s with reasoning on and about 400 ms on a non-reasoning route (OpenRouter, Experiential, NanoGPT all agree on the pattern). Route default effort differs per lane (`none`, `high`, `max` for the same model), so the provider adapter must also pin effort.

**Prefix contract.** Provider caches key on exact bytes in the order tools, system, messages. `core/prompt/prefix.py` fixes the canonical form and hashes it; volatile context rides the final user message. Minimum prefix is 1,024 tokens to clear every provider's floor. Structured-output mode invalidates Anthropic's cache, so the moment read runs on its own model and schema.

**Reverses if.** A talker model is found whose quality needs reasoning at under 700 ms p50 with thinking on, measured on the real prefix.
