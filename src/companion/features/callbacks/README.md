# Callbacks

The callback score: did a reply bring up a memory on its own, and did that land. A measurement
over its replies; nothing reaches the talker.

| File | What |
|---|---|
| `logic.py` | pure: the judge's prompt, parsing a verdict, the report |
| `run.py` | effects: judging new replies within a spend cap, each turn once (`check_new`) |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/0014_callback_checks.sql`) |

Its prompt stays in `src/companion/prompts/` (`system/callback-judge`). `uv run companion
callbacks` judges recent replies and prints the report.

## How it works

Each reply is read by a judge beside the memories its stored card held (`core/card.py`
`memories_from_card`). The report puts precision first: of the callbacks it made, how many were
accurate, fitting and not forced, since a wrong callback hurts more than a missed one.
