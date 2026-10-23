# Reminders (J50)

Reminders and check-ins they ask for, one-off only, live (`COMPANION_REMINDERS`, on unless `off`).

| File | What |
|---|---|
| `logic.py` | pure: reading the parts of when, working out the time, the notes and the send instruction |
| `run.py` | effects: the turn's look-up and note (`REMINDERS`), acting on a read, sending when due |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/0026_reminders.sql`) |
| `cli.py` | `companion reminders`, `--cancel ID` |

Its prompts stay in `src/companion/prompts/` (`system/reminder-read`, `system/reminder-send`,
`notes/reminder-*`), with every other prompt.

How it works:

Reminders they ask for are live, one-off only. A
message with reminder words, or the answer when it just asked when, is read by `system/reminder-read`
into their words for the thing and the parts of when; code works out the time in the machine's named
zone (`named_zone`, so a time after a clock change keeps its wall time) and asks instead of guessing (a
bare "at 8" with both still ahead, "next friday", a time gone, past sixty days, a repeating one). One
note says it was set, with the time code worked out, or what to ask, or that one was cancelled. Every
minute due ones are claimed once, written by the everyday talker with `system/reminder-send` as the tail,
drawn once more on a code-check fail, and sent; their words go out marked when the talker fails or the
cap is reached. A pretend scene holds them until it ends; one missed while the bot was down by over two
hours is let go. A check-in with no time is set at a time picked once between 4 and 8 pm and confirmed
only as the part of the day ("Thursday evening"). `companion reminders` lists them, `--cancel ID`
drops one; `COMPANION_REMINDERS=off`.
