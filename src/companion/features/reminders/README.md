# Reminders (J50)

A reminder, check-in or greeting they ask for in the chat ("remind me at 8 to take the dog out", "check in on me in a few days", "tell me good morning every day"), once or repeating, sent later in the companion's own voice. It exists so a plain request lands at the time they meant, with code and not the model owning the clock.

**Status:** live. Switch: `COMPANION_REMINDERS` (`on` default, `off`). Runs before the reply (a look-up and a note), and on a 60-second timer that sends what is due.

## How it works

**Reading a request.** Before the reply, code looks for reminder words in their message (remind, reminder, check in on me, ping me, nudge me, text me, message me, don't let me forget, make sure I, ask me how, tell me at or in, tell me or say good morning or goodnight, stop saying, and similar), or notes that the companion's last reply asked them when. Only then does it ask a small model to read the message (`system/reminder-read`, 8 s limit, one try, with the last 4 messages for context, less any of their messages that already set or cancelled a reminder: shown one, the reader took a comment on that reminder as the same request again, `unhandled` in `run.py`). A fallback model's answer counts as unread. A failed or unreadable read means no reminder this turn and the reply goes on as usual. The model reads slots and never sets the clock: whether it is a set, a cancel or neither, a reminder, a check-in or a greeting, their words for the thing, the parts of when (day words, hour and minute, am or pm if said, part of the day, minutes from now), whether it repeats and how often (`every`: every day, a weekday, or something else). The read runs under the look-up deadline of the turn. A reader that fills a hour of 0 for a time nobody gave is not trusted: hour 0 (and its minute) is dropped unless their words say midnight, 12 am or 00:xx, so the part of the day they named decides, or it asks (`trusted` in `logic.py`). The schema lets an unsaid day count, hour, minute or minutes-from-now be null.

**Working out the time.** Code turns the slots into a time in the machine's named zone (`named_zone`, so a time after a clock change keeps its wall time). The rules:

- Minutes from now are added to now. Otherwise the day is today, tomorrow, a number of days on (3 if none was said), the next time a weekday comes, or a date.
- A part of the day has a fixed hour: morning 9:00, afternoon 15:00, evening 18:00, night 20:00. "Tonight" alone is 20:00.
- A bare hour is the next one still to come. It asks when both the morning and the evening one are still ahead today, or on another day.
- A time with no day that has passed today means tomorrow.
- A reminder with no time asks "what time".
- A check-in with no time is set at a time picked once, at random, from five-minute marks between 16:00 and 20:00, at least 30 minutes ahead. If that window has gone and no day was said, it moves to tomorrow's. It is told back only as the part of the day ("Thursday evening").
- A vague time code filled in ("in a few days", a check-in with no hour) is said back with an offer to change it.

It asks instead of guessing for a bare "at 8" when both are still ahead, "next friday" (this one or the next), a time already gone, a time past 60 days, and, for a repeating request, how often when it is not every day or one day a week, or what time when a reminder or check-in has none (see Repeating ones below). A cancel matches pending one-offs and running series that share a word with what they named (words under 3 letters and filler aside, "goodnight" and "good night" alike), or the only one when nothing is named; a series it names is stopped with its pending one. No match means no note.

**Repeating ones and greetings.** A repeating request is a series (`series` table, `series.py`): every day, or every week on one day ("every friday"). Anything else ("weekdays", "twice a day") asks how often. A greeting is a third kind beside a reminder and a check-in: a message they want as a small ritual ("tell me good morning every day", "say goodnight every night"), whose part of the day is morning, night or other (from the reader's part of the day, or the words of the greeting).

- A time they said is kept as wall time in the named zone, so it holds across a clock change.
- A morning or night greeting with no time goes at a learned time, worked out again each time the next one is made: the median local time of their first message of each day (a day runs from 4:00 to 4:00) over the last 14 days for a morning one, of their last message for a night one (today counts for a morning once they wrote, never for a night), rounded to 5 minutes. With fewer than 3 days of messages it is 9:00 for a morning, 22:00 for a night.
- A part of the day alone ("every evening") has its fixed hour and is said back with an offer to change it. Any other repeating one with no time asks what time.
- Each time it falls is an ordinary row in `reminders` with the series and its number, so claiming, late, expired and sending work as for a one-off. The next is made only once the one before has ended (sent, late, expired, skipped or cancelled), and on a later day than it, so a learned time that moved later never sends twice in a day. A unique index on the series and the number keeps one of each, so making it twice makes one.
- A series' state is its newest event (`active`, `paused`, `stopped`). A cancel that names it stops it and cancels its pending one.

**The note.** One note in the system block (after the mark note and before the crisis, game, calendar and question notes) says what happened: set, with the time code worked out, or what to ask, or that one was cancelled or stopped. A repeating one has its own note (`notes/reminder-repeat`): how often ("every day at 8:00 am", "every Friday at 7:00 am") and when the first goes; a learned time is told only as around when they usually start (or end) their day, the first by its day and part ("tomorrow morning"), never as a clock time. The reply confirms in its own words. The decision is logged as `reminders: set`, `reminders: asked them when` (also the key that marks the next answer as worth reading) or `reminders: cancelled`, with the prompt `name@version`. Every reminder is stored with their quote, the due time in UTC, the local wall time and the zone. Its state is its newest event (`pending`, `claimed`, `sent`, `late`, `expired`, `cancelled`, `skipped`). Nothing is deleted.

**Sending.** Every 60 seconds the timer picks up reminders that are due.

- A greeting is skipped when they already wrote first: a morning one when any message of theirs came since 4:00 that day, any other one when one came in the 2 hours before it. It is claimed, marked `skipped` with the reason and logged as `reminders: skipped`. A reminder or check-in is never skipped.
- A pretend scene in progress holds them until it ends.
- One that fell due before the bot started and is more than 2 hours late is let go, marked `expired` and logged.
- A due one is claimed once in a single statement, so it cannot go out twice.
- The everyday talker writes it with `system/reminder-send` (a greeting: `system/greeting-send`, worded unlike the earlier days' and with no question to answer) as a tail after the history, with the clock line in the system block. If a code check fails (`code_checks` in `core/recheck.py`) it is drawn once more, and the second draw goes out whatever it is.
- If the daily spend cap is reached, the talker cannot be asked, or it says nothing, their words go out marked (a reminder as the alarm clock emoji and the thing, a check-in as a short "how did it go" line, a greeting as their words for it). The reason is stored with the sent event.
- A send that fails puts the reminder back to `pending` to try next minute.
- A sent message is stored as the companion's own, once. One sent more than 5 minutes after its time is marked `late`.
- It is logged as `reminders: sent` or `reminders: sent late`, with who wrote it and the prompt.
- Then each series that is not stopped is brought up to date (`schedule` in `run.py`, `tend` in `series.py`), read again after the sends so a series stopped meanwhile makes no next one. A greeting series sent 3 times since their last message pauses (`reminders: paused`) and makes no next one; once they write again it resumes (`reminders: resumed`) and the next is made. A reminder or check-in series never pauses.

**Never.** It never sends one reminder twice, never makes two pending of one series, never guesses a vague time silently, never lets the model pick the time, and never skips or pauses a reminder or check-in.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the rows (a reminder, a series), reading the parts of when, working out the time, the notes and the send instruction |
| `series.py` | pure: repeating ones, when the next falls, a learned time, when a greeting is skipped, when a series pauses, the repeat note |
| `run.py` | effects: the turn's look-up and note, acting on a read, starting and stopping a series, sending when due, bringing each series up to date (`REMINDERS`, `deliver_due`, `schedule`, `stop`) |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/0026_reminders.sql` and `0035_series.sql`) |
| `cli.py` | `companion reminders`, `--cancel ID` |

## Prompts

- `system/reminder-read`: reads a request into slots, a greeting and how often included. A failed or unreadable answer means no reminder that turn.
- `system/reminder-send`: the tail that tells the talker what to write when a reminder is due. If it fails, their words go out marked.
- `notes/reminder-set`: says it was set, with the time in words.
- `notes/reminder-repeat`: says a repeating one was set, how often, and when the first goes.
- `system/greeting-send`: the tail that tells the talker to send a greeting they asked for.
- `notes/reminder-ask`: says what to ask about the time.
- `notes/reminder-cancelled`: says one was cancelled.

## Commands

- `uv run companion reminders`: lists the repeating ones with their state, how often and when the next goes, then every reminder soonest first, with state, kind, what they said and which series it belongs to.
- `uv run companion reminders --cancel ID`: drops a pending one or stops a series with its pending one (the first characters of its id are enough, and exactly one must match). It is recorded, not deleted.

## Measured

- 2026-10-21: `system/reminder-read` v1 on 41 made-up requests at a fixed time, 41/41 twice, including asks, cancels and 5 lines that must set nothing. The talker wrote 12 due messages, all short, all passed the code checks (`evals/CHANGELOG.md`).
- 2026-10-21: a check-in with no time lands at a picked time between 4 and 8 pm, 41/41 again (`evals/CHANGELOG.md`).
- 2026-10-25: judge bake-off on the live reminders suite (41 cases): Haiku 41, GPT-6 Luna 32, DeepSeek 39. Luna filled optional integers with 0, so "this evening" read as midnight; the schema now lets them be null and hour 0 counts only when they said midnight, which brought Luna to 40 of 41 (commit 2691f18, `evals/CHANGELOG.md`). Haiku stays the judge.

- 2026-10-26: repeating ones, greetings, `system/reminder-read` v2, `notes/reminder-repeat` and `system/greeting-send` are tested in code only (`tests/features/reminders/`); the prompts are not measured yet. `tests/live/test_reminder_read.py` has repeating and greeting cases for that run.

## Tests

`tests/features/reminders/`
