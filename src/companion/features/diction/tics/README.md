# Tics

What its recent replies keep repeating, so the next ones do something different. The note only describes the tic and asks for something else. It never edits a reply.

**Status:** live. No switch. The note is built before the reply and the background check runs after the turn is stored.

## How it works

Two things feed one note, and both come first in the system block, before the length and scene notes.

Code finds repeats on its own, with no model, in `logic.py` (`tic_note`). It names an opening word that 3 or more of its last 5 replies share, and runs of 3 to 5 words that appear in several of its last 6 replies (a 4 or 5 word run in 2 of them, a 3 word run in 3; starting and ending on a real word). On a casual turn it also names a single pet word: 4 letters or more, not an everyday word, in 3 of its last 6 replies outside scenes, in none of their messages in view, and never written as a name or a title in its replies (capitalised mid-sentence), so their topic, or a title it brought up, is never counted. Phrases and pet words share one list of at most 3, in the one note `notes/habit-phrases`, which asks for other words rather than something different.

The model finds the rest. After a reply is stored, a small judge reads its last 6 replies (the 5 before plus the one just sent) in the background, 6 s limit, so the check never delays a reply. It needs at least 4 replies. It names up to 3 habits (90 characters each), each with how many replies it appears in. A habit seen in fewer than 3 replies is dropped, so weak or invented ones never count. What the two of them are talking about (a plan, a place, a title, a name) is never a habit, since a habit is in how it says things, and the same image, promise or line said again in new words counts (`system/habits` v3). A malformed answer is unreadable and a failure means no note.

What the check found is held on the conversation (`kit/tics.py` `TicMemory`) for the next 2 turns, then dropped. Only one check runs at a time. A fast chat may not have the answer yet, and that turn goes without it. The note (`notes/habit-moves`) lists the fresh habits.

Each check is logged as `habit check` with the scorer model, the prompt version, a hash of the inputs and the habits found.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the code counts (openers, phrases, pet words) and their note, and the judge's window, limits, prompt, parsing and note |
| `run.py` | effects: the judge (`TICS_JUDGE`, stored name `habits`), the background check after a turn (`check_tics`), the note, and the `Feature` (`TICS`) |

## Prompts

- `system/habits`: reads the replies and names what repeats. Unreadable or late means no note.
- `notes/habit-moves`: the line that lists the habits and asks for something different.

- `notes/habit-opener`, `notes/habit-phrases`: the code-found notes.

The prompt files, the judge's name and the `habit check` decision key keep their names from before the folder was renamed (kzndotsh/companion#1). `notes/habit-echo` is no longer used: the note was dropped on 2026-10-18 and its code was removed on 2026-11-05.

## Commands

None.

## Measured

- 2026-10-17: a check reading only its own replies could not have fired on restating, which was rare (5 of 71 replies) (`evals/CHANGELOG.md`).
- 2026-10-24: moving the habit note after the history made no difference to a running bit (extends 19/64 in the block, 20/64 after, p = 0.85). Not shipped (`evals/CHANGELOG.md`).
- 2026-10-25: a code count of single pet words (a flagged word ran through 7 of 38 replies), tuned on 301 real turns since 2026-10-20 to name a word on about one casual turn in five (at first one in two, mostly scene and topic words). Its effect on replies is not measured (`evals/CHANGELOG.md`).

## Tests

`tests/features/diction/tics/`
