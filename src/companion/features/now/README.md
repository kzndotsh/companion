# Now (ADR 0024)

What they said is coming, kept until it happens. When they say dinner is coming soon and keep chatting, the reply should not ask how the food tasted two minutes later. The talker cannot tell from the history which announced thing has happened, so code keeps that state and tells it.

**Status:** shadow (review by 2026-11-08, judged on labels that read right on real messages and notes that would have stopped a time skip). Switch: `COMPANION_NOW` (`shadow` default, `on`, `off`). The reader also runs while reaching out is on, because nudges read its labels.

## How it works

**The reader.** Beside any real turn that is not serious (outside a scene, severity below 2, and the listening read ran), once the reply is out, a small model reads their message alone (`system/now`, 8 s, one try, purpose `now`) and labels it: `soon` (something of theirs is about to happen while they are still here: food on its way, a shower or meal shortly, sleep soon), `leaving` (going now and away for a while), `back`, `done` (the thing they said was coming has happened), or `none`. It gives `what`, a short phrase that completes "they said ..." ("dinner is coming soon"), and the minutes it likely takes, clamped to 5 to 180. Each label but `none` is a decision with the key `now: what is happening with them`, holding the phase, what, minutes, their words, the model and the prompt `name@version`. A failed call means no label for that message.

**The state.** What is open now is a fold over the last three hours of labels, oldest first (`open_now` in `core/turn/now.py`): a `soon` or `leaving` opens an item, a `back` or a `done` closes everything before it, and an item also closes once well past its time (three times its minutes, at least 20 minutes, at most 3 hours), when it has most likely happened.

**The note.** Before a reply, outside a scene and the crisis path, while a `soon` item is open, the newest one becomes one line after the history (`notes/now-soon`): "About 2 minutes ago they said dinner is coming soon. It has not happened yet unless they say so." It states the fact and asks nothing, the wording measured against an instruction (which stopped the slip but turned a third of replies into a send-off) and against the card (no effect). A `leaving` item gets no note: if they are writing, they are back. The note is logged once the turn is stored: `now: told it what they said is still coming` when on, `now: would tell it what they said is still coming (shadow, not sent)` in shadow. The reply to the message that says it is coming is not covered, since the reader runs beside that turn.

**Nudges.** A time away for a nudge is an open `leaving` label (`aways` in `features/nudges/logic.py`); the nudge rules are unchanged (`features/nudges/README.md`).

## Files

| File | What |
|---|---|
| `run.py` | effects: the reader beside the turn (`read_now`) and the note before the reply (`now_note`, `NOW`) |
| `cli.py` | `companion now` |

The labels, the fold and the note text are pure, in `core/turn/now.py`, since nudges read them too.

## Prompts

- `system/now`: the reader. A failed or unreadable answer leaves no label.
- `notes/now-soon`: the line after the history while something they said is coming is open.

## Commands

- `uv run companion now`: their labelled messages of the last three days, what is open now, and the notes sent or logged in shadow.

## Measured

- 2026-10-25: on the flagged turn, 30 to 150 replies a version on the live talker: the slip came in 20 of 140 with nothing, 8 of 150 with this note (a real difference), 0 of 120 with an instructing note that turned 43 of 120 into a send-off, and 10 of 60 with the same line on the card (`evals/CHANGELOG.md`).

## Tests

`tests/features/now/`, `tests/core/turn/test_now.py`
