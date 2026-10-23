# Nudges

A light nudge when they step away and stay gone longer than they said. Shadow only: drafted and
recorded, never sent (`COMPANION_INITIATIVE`, `off` to disable).

| File | What |
|---|---|
| `logic.py` | pure: reading "stepping away", when a nudge is due, the draft prompt |
| `run.py` | effects: the stepping-away read beside the turn (`NUDGES`), and the tick that drafts a nudge |

Its prompts stay in `src/companion/prompts/` (`system/away`, `system/nudge-draft`). Read what it
would have sent with `uv run companion initiative`.

## How it works

When they say they are stepping away now ("shower time", "brb"; `system/away`, read beside any
real, not serious turn, 8 s limit) and then stay quiet at least twice as long as that and an hour,
the 15-minute tick drafts one light nudge (`system/nudge-draft`): one per time away, never in quiet
hours, never after a goodbye, gone after six hours, at most two a day, and any message from them
cancels it.
