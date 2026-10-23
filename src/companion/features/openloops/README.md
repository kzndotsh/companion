# Open loops (J15, ADR 0015)

Things they said about their near future that a friend would ask about later, and whether to reach
out about one. Reach-outs run in shadow (`COMPANION_INITIATIVE`, `off` to disable); the note when
they next write is live.

| File | What |
|---|---|
| `logic.py` | pure: which plans become loops, their kinds and times, the note |
| `gate.py` | pure: whether to reach out now, and about what (ADR 0015) |
| `run.py` | effects: reading new messages for loops, the 15-minute tick, the note (`OPENLOOPS`) |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/0012_open_loops.sql`) |

Its prompts stay in `src/companion/prompts/` (`system/openloops`, `system/openloops-draft`). The
caps every reach-out keeps to are in `core/reachout.py`, shared with nudges. `uv run companion
initiative` lists the loops and what shadow mode would have sent.

## How it works

How plans become loops, when each is due, the note when they write and the gate in front of a
reach-out are described in `docs/initiative.md`.
