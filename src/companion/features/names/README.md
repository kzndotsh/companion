# Names

| File | What |
|---|---|
| `logic.py` | pure: its rules, prompts' parsing and notes |
| `run.py` | effects: its `Feature` and what it does with the store and models |
| `cli.py` | its `companion` command |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/`) |

Its prompts stay in `src/companion/prompts/`.

## How it works

Things they name are matched in shadow (fetch on mention, `features/names/logic.py`): after each
memory pass a small model lists the names in new memories with the other words for each
(`system/memory-names`), and on every ordinary turn code matches their message as whole words and
logs the memories about each name that the card left out. Nothing reaches the talker; `companion
names` shows the list and the count.
