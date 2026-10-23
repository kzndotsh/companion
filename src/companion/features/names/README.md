# Names

| File | What |
|---|---|
| `logic.py` | pure: its rules, prompts' parsing and notes |
| `run.py` | effects: its `Feature` and what it does with the store and models |
| `cli.py` | its `companion` command |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/`) |

How it works is described in `docs/features.md`. Its prompts stay in `src/companion/prompts/`.
