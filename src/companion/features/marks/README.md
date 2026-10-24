# Marks

Its own emoticons and kaomoji, offered by code now and then so it has marks of its own instead of
only copying theirs. Live, `COMPANION_MARKS` (on unless `off`).

| File | What |
|---|---|
| `logic.py` | pure: when a turn offers a mark, which one (never theirs, never one it used lately) |
| `marks.txt` | the marks, one per line (kept as text: they are made of look-alike characters) |
| `run.py` | effects: the note after the history on a casual turn, logged with the mark (`MARKS`) |

Its prompt stays in `src/companion/prompts/` (`notes/own-mark`). Measure it with the eval flag
`+mark`.

## How it works

On a casual turn (not serious, not a scene, not a goodbye), a mark is offered when their message has
an emoticon, and on about one other turn in four (drawn from the turn id, so a replay draws the
same). Code picks one of the marks at random, leaving out any in their message or in its last six
replies, and one line after the history offers it. Measured 2026-10-23 (`evals/CHANGELOG.md`): after
the history it used one in 66 of 80 replies, 20 different marks; in the system block, 10 of 80. It
does not stop it copying their mark (about 60% on the copying fixtures either way): that habit is the
model's, with their mark last in view. Emoji are left to it: it already chooses its own.
