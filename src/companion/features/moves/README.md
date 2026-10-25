# Moves

What its recent replies keep repeating, so the next ones do something different. The note only describes the habit and asks for something else. It never edits a reply.

**Status:** live. No switch. The note is built before the reply and the background check runs after the turn is stored.

## How it works

Two things feed one note, and both come first in the system block, before the length and scene notes.

Code finds repeats on its own, with no model, in `core/turn/habits.py`. It names an opening word that 3 or more of its last 5 replies share, and runs of 3 to 5 words that appear in several of its last 6 replies (up to 3 phrases, starting and ending on a real word). On a casual turn it also names a single pet word: 4 letters or more, not an everyday word, in 3 of its last 6 replies outside scenes, and in none of their messages in view, so their topic is never counted. A message of theirs with an emoji or emoticon gets an echo note, but that note is sent elsewhere.

The model finds the rest. After a reply is stored, a small judge reads its last 6 replies (the 5 before plus the one just sent) in the background, 6 s limit, so the check never delays a reply. It needs at least 4 replies. It names up to 3 habits (90 characters each), each with how many replies it appears in. A habit seen in fewer than 3 replies is dropped, so weak or invented ones never count. A malformed answer is unreadable and a failure means no note.

What the check found is held on the conversation (`loops/habits.py` `HabitMemory`) for the next 2 turns, then dropped. Only one check runs at a time. A fast chat may not have the answer yet, and that turn goes without it. The note (`notes/habit-moves`) lists the fresh habits.

Each check is logged as `habit check` with the scorer model, the prompt version, a hash of the inputs and the habits found.

## Files

| File | What |
|---|---|
| `logic.py` | pure: window and limits, which replies to read, the judge prompt, parsing, the note |
| `run.py` | effects: the judge (`HABITS`), the background check after a turn (`check_habits`), the note, and the `Feature` (`MOVES`) |

## Prompts

- `system/habits`: reads the replies and names what repeats. Unreadable or late means no note.
- `notes/habit-moves`: the line that lists the habits and asks for something different.

The code-found notes (`notes/habit-opener`, `notes/habit-phrases`, `notes/habit-echo`) are loaded from `core/turn/habits.py`.

## Commands

None.

## Measured

- 2026-10-17: a check reading only its own replies could not have fired on restating, which was rare (5 of 71 replies) (`evals/CHANGELOG.md`).
- 2026-10-24: moving the habit note after the history made no difference to a running bit (extends 19/64 in the block, 20/64 after, p = 0.85). Not shipped (`evals/CHANGELOG.md`).

## Tests

`tests/features/moves/`
