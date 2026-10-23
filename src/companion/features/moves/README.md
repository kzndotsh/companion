# Moves

What its recent replies keep repeating, so the next ones do something different. Live.

| File | What |
|---|---|
| `logic.py` | pure: the judge's prompt, parsing, which replies to read, the note |
| `run.py` | effects: the background check once a reply is stored (`check_habits`), the note, `MOVES` |

Its prompts stay in `src/companion/prompts/` (`system/habits`, `notes/habit-moves`). The openings and
moves code finds on its own are in `core/turn/habits.py`; what the last check found is held on the
conversation (`loops/habits.py` `HabitMemory`) for two turns.

## How it works

After each reply is stored, its last few replies are read in the background by a small judge, so the
check never delays a reply; a fast chat may not have the answer yet, and the next turn goes without
it. The note comes first in the system block, before the length and scene notes.
