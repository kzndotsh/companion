# A calendar of occasions: days worth a word, chosen by code

**Status (2026-10-25):** phase 1 built as `src/companion/features/calendar/` (`COMPANION_CALENDAR`,
on): US public and cultural days, the relationship's dates and lead-ups to the big days, as a note
after the history. Their own yearly dates from memory were added the same day (R19). Seasons and other calendar
moments, the region, and "a day" as a reach-out kind are not built.

Not a task yet. A plan from 2026-10-25, for a feature that gives the companion natural reasons to
talk: holidays, seasons, their own dates and the relationship's.

## Why

Since 2026-10-25 the clock line gives the full date, but the date alone does not make it notice a
day. Scripted first messages on Halloween (morning and evening), 12 draws each on the live talker:
it mentioned Halloween **0/12** with the date in the clock line, **0/12** with "(Halloween)" added to
the clock line, and **12/12** with one short note after the history ("Today is Halloween. If it
fits, a light nod to it is welcome"); an ordinary morning 0/12. The replies read naturally ("happy
halloween, got anything fun planned?"). So, as with other notes (ADR 0014), code knows the day and a
note after the history makes it count.

## What counts as an occasion (sources)

1. **Public and cultural days.** The `holidays` Python library (offline, maintained, per country and
   subdivision) has a PUBLIC category and an UNOFFICIAL one for widely observed cultural days
   (Halloween, Valentine's Day, St Patrick's Day) that deliberately leaves out marketing "national
   days". Region: the US by default until where they live is known (a location shared once, or a
   basic from `docs/inbox/2026-10-25-what-else-it-could-learn-about-them.md`).
2. **Calendar moments, in code:** New Year's Eve, the first day of a season, the clocks changing,
   a Friday evening or the start of a weekend, a long weekend. Small and general.
3. **Their own dates, from memory:** a birthday, an anniversary, a yearly date they named. Open loops
   already handle one-off plans on a day (ADR 0015's celebrate and encourage kinds); the calendar
   takes the ones that come round every year.
4. **The relationship's dates:** a month since they first talked, a hundred days, a year, worked out
   from the first message in the ledger.


## How it reaches the conversation (channels)

- **A note after the history,** on the first casual turn of the day (not serious, not a scene, not a
  goodbye): "Today is X. If it fits, a light nod to it is welcome." Once a day per occasion, at most
  one occasion a turn, chosen by a fixed order (their own and the relationship's dates first, then
  public days, then calendar moments).
- **A lead-up,** once, a day or two before a big one ("Halloween is in two days"), so it can ask about
  plans the way a friend does. Optional.
- **A reason to reach out first** (ADR 0021): "a day" as a new kind, so on the morning of their
  birthday or a holiday it may text first. Shadow first, like the other kinds; the same gate and
  never-rules apply.

## Rules (in code)

- Code picks the occasion and logs it with its source; a model only words it.
- Never assume a celebration: the note says "if it fits", and never presumes family, plans or a
  religion. A day memory shows they keep (they said they celebrate it) may be named more warmly.
- Holidays can be lonely. Surveys around Christmas find a real share of people spend it alone and
  feel a stigma about it; the note stays light and asks nothing that assumes company.
- Hard dates (a death, a loss) are never raised by the calendar. A sensitive memory's date may only
  make the mood tender (ADR 0016), never be mentioned unprompted.
- Not on a serious turn, not in a scene, not in the crisis path; the crisis path holds it.
- At most one occasion note a day, and none when another note asks them something that turn.

## Data shape

```
Occasion(name, day, kind, source, how)
  kind:   public | cultural | season | personal | relationship | own
  source: holidays:US | code | memory:<belief id> | ledger:first-message | sheet
  how:    on_the_day | lead_up
calendar.occasions(today, region, personal, first_met) -> list[Occasion]   # pure
calendar.pick(occasions, offered_today, turn) -> Occasion | None           # pure, the one for this turn
```

A feature folder (`features/calendar/`): `logic.py` (pure: the sources, the order, the pick),
`run.py` (the note and its log), `cli.py` (`companion calendar`: the next 30 days of occasions and
what it said on each), a README.

## How it is measured

Scripted fixtures through the turn's own path (`evals/sample.py`): Halloween, Christmas, US
Thanksgiving, New Year's Eve, a birthday from memory, a one-month anniversary, an ordinary day, a
serious message on a holiday and a scene on a holiday; 12 draws each on the plain persona and the
owner's character. Measured: how often it names the day; whether it assumes plans, family or a
religion (blind Claude judges); never on the serious or scene turns; and no repeat later that day.

## Phases

1. **Public and cultural days, in chat,** US by default, before Halloween (2026-10-31).
2. **Their own and the relationship's dates.**
3. **"A day" as a reason to reach out,** in shadow with the other kinds.
4. **Region** from a shared location.
5. **Lead-ups and calendar moments,** if the first phases land well.

## Questions for the owner

1. Which days: the public and cultural set for the US (including Christmas and Easter, worded "if it
   fits"), or only the cultural ones until it knows what they celebrate?
2. The relationship's dates (a month, a hundred days, a year): welcome, or too much?
3. Lead-ups ("Halloween is in two days"): yes or no?
4. Settled: no birthday of its own. One tied to the day they first talked was considered and dropped
   (2026-10-25): next to a character's stated age it would confuse more than it adds. The first day
   stays available only as the relationship's anniversary (question 2).

## Sources

- python-holidays documentation, holiday categories (PUBLIC, UNOFFICIAL).
- Surveys on spending Christmas alone (BPS and YouGov 2022; Age Scotland 2019; a 2025 poll of adults
  who live alone), as reported; the national totals are unverified.
