# Calendar

Days worth a word: US public and cultural days, the lead-up to a big one, and the relationship's own dates, offered as one note after the history. It exists because the date in the clock line alone made it name Halloween in 0 of 12 replies, and a short note after the history in 12 of 12 (`docs/inbox/2026-10-25-a-calendar-of-occasions.md`).

**Status:** live. Switch: `COMPANION_CALENDAR` (`on` default, `off`). Runs before the reply, as a note sent after the history on a casual turn. No model call is made.

## How it works

**The occasions.** Code works out what today holds, in the machine's named zone (`named_zone`):

- **Public and cultural days** come from the `holidays` library for the region (`REGION`, "US", set in one place): its `PUBLIC` category (New Year's Day, Martin Luther King Jr. Day, Presidents' Day, Memorial Day, Juneteenth, Independence Day, Labor Day, Columbus Day, Veterans Day, Thanksgiving, Christmas Day) and its `UNOFFICIAL` one (Groundhog Day, Valentine's Day, St. Patrick's Day, Good Friday, Easter, Mother's Day, Father's Day, Halloween, Christmas Eve, New Year's Eve). Observed stand-ins (a Friday off for a Saturday holiday) are left out. Names are put in plain words (`PLAIN`). New Year's Eve, Christmas Eve, Mother's Day and Father's Day are also written in code and used only when the library lacks them for the region.
- **The relationship's dates** come from the local date of their first message in the ledger: a month, a hundred days, six months, a year and each year after. A month past a short month's end lands on its last day (31 January, then 28 or 29 February).
- **Lead-ups** for the big days (New Year's Eve, Valentine's Day, Halloween, Thanksgiving, Christmas Day): two days before ("in two days") and the day before ("tomorrow").

**The pick.** At most one occasion a turn, in a fixed order: the relationship's date, then a public or cultural day, then a lead-up. An occasion is never offered twice: each on its day once, and a lead-up once per big day in total (both lead-up days share one key). What was offered is read from the decisions of the last three days.

**The note.** On a casual turn (the listening judge read it as not serious, outside a scene, not a goodbye, and no crisis concern), not held by the floor, with no name question, check-in, open loop, crisis note or question game that turn, the picked occasion becomes one line after the history:

- a public or cultural day: `notes/occasion-day` ("Today is Halloween. If it fits, a light nod to it is welcome...", never assuming they celebrate it, have plans or have family around);
- a lead-up: `notes/occasion-soon` ("Halloween is in two days. If it fits, you could lightly ask whether they have anything planned...");
- the relationship's date: `notes/occasion-us` ("It has been a month since the two of you first talked...").

The calendar counts as a note that asks them something (`ASKING` in `loops/features.py`), so the question-run note stays out on that turn. Once the turn is stored the offer is logged as `calendar: offered`, with the occasion's key, name, day, kind, how, when and region. A failed turn offers nothing and uses nothing up.

**Never.** It never assumes a celebration, a religion, plans or company; never on a serious turn, in a scene, on a goodbye or on a turn the crisis path reads as a risk; never more than one occasion a turn; never a hard date from memory.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the occasions for a day (`occasions`), the relationship's dates (`together`, `add_months`), the pick (`pick`), the note text (`note`), `REGION`, `OFFERED` |
| `run.py` | effects: the note after the history on a casual turn, logged once the turn is stored (`CALENDAR`) |
| `store.py` | its queries: the time of their first message, and the occasions offered since a time |
| `cli.py` | `companion calendar` |

## Prompts

- `notes/occasion-day`: today is a public or cultural day. There is no judge, so there is no failure to read.
- `notes/occasion-soon`: a big day is tomorrow or in two days.
- `notes/occasion-us`: a month, a hundred days, six months or a year since they first talked.

## Commands

- `uv run companion calendar`: the occasions in the next 30 days, lead-ups included, and what was offered in the last 30, from the decisions.

## Measured

- 2026-10-25: scripted first messages on 12 days, 6 draws each, owner's character: the first wording (with "don't assume they celebrate it") named Thanksgiving 0/6, New Year's Eve 1/6 and a one-month date 0/6 and hedged ("merry christmas, if you're celebrating"); the direct wording named every day 6/6, and on a lonely Christmas message it kept to comfort ("christmas can make the quiet feel louder"). It also wished a "happy Memorial Day" and a "happy Good Friday", so days of remembrance, civic, religious and contested days are left out (`LEFT_OUT`).
- 2026-10-25: scripted Halloween first messages, 12 draws each on the live talker: it named the day 0/12 with the date in the clock line, 0/12 with "(Halloween)" in the clock line, 12/12 with a note after the history; an ordinary morning 0/12 (`docs/inbox/2026-10-25-a-calendar-of-occasions.md`). The shipped wording, lead-ups and the relationship's dates are not yet measured.

## Tests

`tests/features/calendar/`
