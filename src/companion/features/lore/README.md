# Lore

| File | What |
|---|---|
| `logic.py` | pure: its rules, prompts' parsing and notes |
| `run.py` | effects: its `Feature` and what it does with the store and models |
| `cli.py` | its `companion` command |

Its prompts stay in `src/companion/prompts/`.

## How it works

The companion's own lore lives in its views (ADR 0020): after each memory pass a small model labels
each new view of its own as taste, stance, rule, self or lived (`system/lore-label`,
`features/lore/logic.py`); only a taste is lore, a lived claim never is; `companion lore` lists the
tastes. On an ordinary turn (not serious, not a scene, not a goodbye) code embeds their message and
shows it at most two of its tastes at 0.3 or more, as the words it said (`notes/lore`,
`COMPANION_LORE` on, shadow or off). Next: a consistency check on new tastes.
