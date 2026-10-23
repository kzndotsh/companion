# Merging (ADR 0019)

Memories about one thing (one moment split into pieces, one interest restated), proposed as one.
Nothing is merged automatically: each agreed group is a question for the owner.

| File | What |
|---|---|
| `logic.py` | pure: the prompts, what counts as an agreed group, the merged kind |
| `run.py` | effects: grouping the last two days each night (`recent`), the whole store (`everything`) |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/`) |

Its prompts stay in `src/companion/prompts/` (`system/memory-group`, `system/memory-merge`).
`uv run companion memory group` groups the whole store; the owner answers in `memory review`
(`cli/memory.py`, shared with consolidate), or merges by hand with `companion merge`.

## How it works

Described with the rest of memory over time in `docs/memory.md`.
