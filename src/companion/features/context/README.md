# Context

| File | What |
|---|---|
| `logic.py` | pure: its rules, prompts' parsing and notes |
| `run.py` | effects: its `Feature` and what it does with the store and models |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/`) |

Its prompts stay in `src/companion/prompts/`.

## How it works

After each memory pass, feelings and sensitive memories get a short note on what was being talked
about (`system/memory-context`, `features/context/logic.py`, J51), shown beside them on the card.
