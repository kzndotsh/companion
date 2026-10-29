# Calendar

Days worth a word: their own yearly dates from memory, US public and cultural days, the lead-up to a big one or one of theirs, and the relationship's own dates, offered as one note after the history. It exists because the date in the clock line alone made it name Halloween in 0 of 12 replies, and a short note after the history in 12 of 12 (`docs/inbox/2026-10-25-a-calendar-of-occasions.md`).

**Status:** live. Switch: `COMPANION_CALENDAR` (`on` default, `off`). Runs before the reply as a candidate for the mention picker (`turn/mention.py`), which may bring it up as one line after the history on a casual turn. No model call is made.

## How it works

**The occasions.** Code works out what today holds, in the machine's named zone (`named_zone`):

- **Public and cultural days** come from the `holidays` library for the region (`REGION`, "US", set in one place): its `PUBLIC` category and its `UNOFFICIAL` one, with observed stand-ins (a Friday off for a Saturday holiday) left out. Names are put in plain words (`PLAIN`). Days of remembrance, civic, religious and contested days are then dropped (`LEFT_OUT`: Martin Luther King Jr. Day, Presidents' Day, Memorial Day, Juneteenth, Columbus Day, Veterans Day, Good Friday). What is left: New Year's Day, Groundhog Day, Valentine's Day, St. Patrick's Day, Easter, Mother's Day, Father's Day, Independence Day, Labor Day, Halloween, Thanksgiving, Christmas Eve, Christmas Day and New Year's Eve. New Year's Eve, Christmas Eve, Mother's Day and Father's Day are also written in code and used only when the library lacks them for the region.
- **The relationship's dates** come from the local date of their first message in the ledger: a month, a hundred days, six months, a year and each year after. A month past a short month's end lands on its last day (31 January, then 28 or 29 February).
- **Their own dates** come from what memory holds about them (`their_dates`, `yearly`; card R19): a memory that names a birthday or an anniversary on a month and a day ("December 4th", "the 3rd of March") is a yearly date, theirs unless someone else's is named ("their sister's birthday"). A memory said in a scene, one at sensitivity 2 or more, and any date tied to a loss (a death, a funeral, a breakup, a diagnosis, by word) never give one. No model call: code reads the words, so a date memory words oddly is missed rather than guessed. The 29th of February is the 28th in other years.
- **Lead-ups** for their own dates and the big days (New Year's Eve, Valentine's Day, Halloween, Thanksgiving, Christmas Day): two days before ("in two days") and the day before ("tomorrow").

**The pick.** At most one occasion a turn, in a fixed order: one of theirs, the relationship's date, a public or cultural day, then a lead-up (one of theirs before a big day's). An occasion is never offered twice: each on its day once, and a lead-up once per big day in total (both lead-up days share one key). What was offered is read from the decisions of the last three days.

**The note.** The picked occasion is the calendar's candidate (`calendar_candidate`, `Feature.mention`) for the one thing brought up on its own; the picker in `turn/mention.py` decides across the calendar and plans (ADR 0023): on a casual turn, not held, with no earlier note asking them something, the best by rank (their own day, then the relationship's, then a public or cultural day, then a lead-up, with plans ranked among them), one a day across sources unless the new one ranks higher. A brought-up occasion is one line after the history:

- a public or cultural day: `notes/occasion-day` ("Today is Halloween. If it fits, a light nod to it is welcome...", never assuming they celebrate it, have plans or have family around);
- a lead-up: `notes/occasion-soon` ("Halloween is in two days. If it fits, you could lightly ask whether they have anything planned...");
- one of their dates: `notes/occasion-theirs` ("Today is their birthday. Mark it warmly in a few words...", never saying it remembered or looked it up); its lead-up uses `notes/occasion-soon`;
- the relationship's date: `notes/occasion-us` ("It has been a month since the two of you first talked...").

What the picker brings up asks them something (its offer says `asks`), so the question-run note stays out on that turn. Once the turn is stored the offer is logged as `calendar: offered`, with the occasion's key, name, day, kind, how, when, region, its rank and what the learned pace said. A failed turn offers nothing and uses nothing up.

**Never.** It never assumes a celebration, a religion, plans or company; never on a serious turn, in a scene, on a goodbye or on a turn the crisis path reads as a risk; never more than one occasion a turn; never a sensitive date or one tied to a loss from memory.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the occasions for a day (`occasions`), their dates from memory (`yearly`, `their_dates`, `Dated`), the relationship's dates (`together`, `add_months`), the pick (`pick`), the note text (`note`), `REGION`, `OFFERED` |
| `run.py` | effects: their dates read from memory (`theirs`), the occasion as a candidate for the picker with its rank (`calendar_candidate`, `rank`, `CALENDAR`) |
| `store.py` | its queries: the time of their first message, and the occasions offered since a time |
| `cli.py` | `companion calendar` |

## Prompts

- `notes/occasion-day`: today is a public or cultural day. There is no judge, so there is no failure to read.
- `notes/occasion-soon`: a big day is tomorrow or in two days.
- `notes/occasion-us`: a month, a hundred days, six months or a year since they first talked.
- `notes/occasion-theirs`: today is one of their dates from memory.

## Commands

- `uv run companion calendar`: their dates from memory, the occasions in the next 30 days, lead-ups included, and what was offered in the last 30, from the decisions.

## Measured

- 2026-10-25: scripted first messages on 12 days, 6 draws each, owner's character: the first wording (with "don't assume they celebrate it") named Thanksgiving 0/6, New Year's Eve 1/6 and a one-month date 0/6 and hedged ("merry christmas, if you're celebrating"); the direct wording named every day 6/6, and on a lonely Christmas message it kept to comfort ("christmas can make the quiet feel louder"). It also wished a "happy Memorial Day" and a "happy Good Friday", so days of remembrance, civic, religious and contested days are left out (`LEFT_OUT`).
- 2026-10-25: scripted Halloween first messages, 12 draws each on the live talker: it named the day 0/12 with the date in the clock line, 0/12 with "(Halloween)" in the clock line, 12/12 with a note after the history; an ordinary morning 0/12 (`docs/inbox/2026-10-25-a-calendar-of-occasions.md`, `evals/CHANGELOG.md`, about $0.06).
- 2026-10-25: the shipped notes replayed on the same 12 days: every day named 6 of 6 (commit 8c4ec26). Lead-ups on a real conversation are not yet measured.
- 2026-10-25: their birthday on a casual "good morning" (`occasion-their-birthday-on-the-day`), 12 draws on the live talker: 12/12 wished them a happy birthday warmly in a line and never said it remembered, against 0/12 without the note (a real difference). The canned-reaction check redrew 10 of the 12, reading the birthday wish as a stock line; the redraws read as well (for its review, Q3). On the real memory the reader finds one date, their birthday.

## Tests

`tests/features/calendar/`
