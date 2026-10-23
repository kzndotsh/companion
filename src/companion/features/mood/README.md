# Mood (ADR 0016)

A mood that carries: cozy, tender or playful, owned by code, shown only in behaviour. Each message of
theirs adds effects, and the mood is worked out from them when it is read (`COMPANION_MOOD` is on,
shadow or off).

| File | What |
|---|---|
| `logic.py` | pure: the states, what each message adds, how effects fade, the line and its reason |
| `run.py` | effects: the note (`mood_offer`) and the effects written once the turn is stored, `MOOD` |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/0015_mood_effects.sql`) |
| `cli.py` | `companion mood`, `--replay DAYS` |

Its notes stay in `src/companion/prompts/` (`notes/mood-*`). How texting energy is read is in
`core/turn/energy.py`; the goodbye check it shares with the turn is `core/turn/goodbye.py`.

## How it works

Described with the reply path in `docs/turn.md`.
