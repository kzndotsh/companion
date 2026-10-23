# Episodes

| File | What |
|---|---|
| `logic.py` | pure: its rules, prompts' parsing and notes |
| `run.py` | effects: its `Feature` and what it does with the store and models |
| `cli.py` | its `companion` command |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/`) |

Its prompts stay in `src/companion/prompts/`.

## How it works

The times they spent together are recorded (J12, `features/episodes/logic.py`): the chat is cut into
stretches at a 2-hour gap or a turn into or out of a pretend scene lasting 20 messages; code works
out the length, the kind (everyday, scene, heavy), the most serious moment and firsts, and
`system/episode-gist` writes one sentence on the shape of it and how it ended, never its details.
Written nightly and by `companion episodes --write`; a newer prompt's line supersedes an older one.
When their message points at a time ("last night", "today") or they come back after 3 hours, the
lines for that time (or the last one) are chosen by code, logged, and ride the system block
(`notes/recent-times`; `COMPANION_EPISODES` on by default, `shadow` only logs, `off` stops it). The
owner read the lines and turned it on, 2026-10-22.
