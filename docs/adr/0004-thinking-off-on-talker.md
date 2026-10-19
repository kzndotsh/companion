# 0004. The talker never reasons

**Status:** accepted 2026-10-15. The prefix contract was changed in part by ADR 0012 (see below).

## Decision

The fast loop's talker is called with thinking disabled. `TalkerRequest` has no thinking field, so
a caller cannot ask for it. Reasoning, where it is wanted, belongs off the fast path.

The provider adapters send it disabled on every call (`models/openrouter.py`, `models/kiro.py`).
Evals can turn it on for a measurement (`+low`, `+medium`, `+high` in a variant), and the
OpenRouter adapter then pins that effort, but the live talker never does.

## Why

Every fast tier measured reasoned by default. In the speed audit, Haiku 5.5's first answer token
took 7.7 s with reasoning on and about 400 ms on a non-reasoning route (OpenRouter, Experiential
and NanoGPT all agreed on the pattern). A route's default effort also differs per lane (`none`,
`high`, `max` for the same model), so the adapter must pin it and not trust the default.

## Prefix contract

Provider caches key on exact bytes, in the order tools, system, messages.

- `core/prompt/prefix.py` fixes the canonical form of the persona and tools and hashes it.
- `MIN_PREFIX_TOKENS` is 1,024, Anthropic's floor for most models but not for Haiku 4.5. Measured
  on 2026-10-15 through OpenRouter, a 2.8k-token prompt was never cached and a 6.6k-token prompt
  was (`tests/live/test_cache.py`). The real floor lies between and is probably 4,096.
- Structured-output mode invalidates Anthropic's cache, so the moment read runs on its own model
  and schema.
- At the time, a persona-only prefix of about 1.6k tokens plus a 40-message window (3.2k to 3.8k)
  never reached the floor, so v1 paid full input price (about $0.0035 per turn). That was accepted
  until the state card or a larger window pushed the prompt past it.

## Since

- 2026-10-19, superseded in part by ADR 0012: volatile context no longer rides the final user
  message. The clock, the memory card and the notes go in a system block after the persona, so the
  persona prefix stays byte-stable. The wire adapter also puts a cache breakpoint on the last
  message before the new user turn (`models/wire.py`).
- The live talker is no longer Haiku. The everyday default is `openai/gpt-6-luna` and the roleplay
  talker is `deepseek/deepseek-v4.1-flash` (`COMPANION_MODEL`, `COMPANION_ROLEPLAY_MODEL`). Judges
  and extraction run on Haiku 5.5. The no-reasoning rule applies to all of them.
- The persona is now about 10k characters (v40), roughly 2.5k tokens by the code's estimate.

## Reverses if

A talker model is found whose quality needs reasoning at under 700 ms p50 with thinking on,
measured on the real prefix.
