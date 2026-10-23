# Consolidate (ADR 0019)

Memory checking itself: each night, memories a week old are read for whether they still hold; when
the memory pass writes a new memory, it is read against its nearest existing one. In shadow unless
`COMPANION_CONSOLIDATE=on`.

| File | What |
|---|---|
| `logic.py` | pure: the prompts, the labels (`Label`, `Relation`), what counts as agreed |
| `run.py` | effects: the nightly check (`nightly`), the write-time pair check (`SameCheck`) |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/`) |

Its prompts stay in `src/companion/prompts/`. What it raises, the owner answers with `uv run
companion memory review` (`cli/memory.py`, shared with merging).

## How it works

Described with the rest of memory over time in `docs/memory.md`.
