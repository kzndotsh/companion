# 0004. The talker never reasons

**Status:** accepted 2026-10-15.

**Decision.** The fast loop's talker is called with thinking disabled. `TalkerRequest` has no thinking field, so a caller cannot ask for it. Reasoning belongs to the slow loop's thinker.

**Why.** Every current fast tier reasons by default. Measured in the speed audit: Haiku 5.5 first answer token is 7.7 s with reasoning on and about 400 ms on a non-reasoning route (OpenRouter, Experiential, NanoGPT all agree on the pattern). Route default effort differs per lane (`none`, `high`, `max` for the same model), so the provider adapter must also pin effort.

**Prefix contract.** Provider caches key on exact bytes in the order tools, system, messages. `core/prompt/prefix.py` fixes the canonical form and hashes it; volatile context rides the final user message. `MIN_PREFIX_TOKENS` is 1,024, which is Anthropic's floor for most models but not for Haiku 4.5: measured on 2026-10-15 through OpenRouter, a 2.8k-token prompt was never cached and a 6.6k-token prompt was (`tests/live/test_cache.py`). The real floor lies between and is probably 4,096. A persona-only prefix of about 1.6k tokens plus a 40-message window (3.2k to 3.8k) never reaches it, so v1 pays full input price (about $0.0035 per turn). That is accepted until the state card or a larger window pushes the prompt past the floor. Structured-output mode invalidates Anthropic's cache, so the moment read runs on its own model and schema.

**Reverses if.** A talker model is found whose quality needs reasoning at under 700 ms p50 with thinking on, measured on the real prefix.
