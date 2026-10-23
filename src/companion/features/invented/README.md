# Invented (G42, J9)

The made-up facts rate: how often a reply states something about them that neither the
conversation nor its memory supports. Measured on demand, never on the reply path.

| File | What |
|---|---|
| `logic.py` | pure: the judge's prompt, which statements count, the rate |
| `run.py` | effects: judging new replies within a spend cap, each turn once (`check_new`) |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/0025_invented_checks.sql`) |

Its prompt stays in `src/companion/prompts/` (`system/invented-judge`).

## How it works

A cheap judge lists each statement about their life with what supports it; code keeps only the
statements quoted from the reply and said to them. On real replies the cheap judge's flags were
right about one time in twelve, so they are candidates: the rate is what a stronger reader confirms.
`uv run companion invented --days 7 --cap 0.2 --dump out.json` writes the candidates for that
reader.
