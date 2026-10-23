# Knowing

| File | What |
|---|---|
| `logic.py` | pure: its rules, prompts' parsing and notes |
| `run.py` | effects: its `Feature` and what it does with the store and models |
| `cli.py` | its `companion` command |

Its prompts stay in `src/companion/prompts/`.

## How it works

How they want to be referred to is a setting (`companion address --set`) pinned after the clock on
every turn. Until memory knows their name, a note on a casual turn (at most daily) asks for it, and
their answer is stored as a belief quoting their words (`features/basics/`, J48). Each memory is
labelled with the part of their life it is about and how personal it is (`system/memory-map`, after
each memory pass); code picks the thinnest part fine to ask about and, on a casual turn at most
daily, only logs it (shadow, `features/knowing/logic.py`). `uv run companion map` shows the map and
the picks. When their own words touch a basic fact without giving it, the hook logs whether it would ask
(`features/hooks/README.md`).
