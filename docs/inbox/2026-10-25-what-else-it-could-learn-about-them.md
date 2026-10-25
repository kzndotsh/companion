# What else it could learn about them, and how

**Status (2026-10-25):** pronouns are built as a basic it asks for after the name
(`src/companion/features/basics/`, `notes/ask-pronouns`). The ideas below are not built.

Not a task. Ideas from 2026-10-25, after pronouns joined the name as a basic it asks for and birthday
and school joined the hook. Each item says what it would feed and how it should be learned: **ask**
(once, lightly, on a casual turn), **ask when touched** (only when their own words open the door),
or **learn only** (picked up from what they say or when they write, never asked).

## How to be with them (the largest effect on replies)

- **Venting: listen or help fix.** Ask once, right after the first real vent. Today the listening
  note infers it every turn from the message alone; a stated preference would steer every serious
  turn after.
- **Nicknames and pet names they like and do not like.** Learn when they react to one ("don't call
  me that"); ask only before it starts using one. A pet name it guessed once ran through an evening.
- **What cheers them up** (a food, a show, a kind of message). Learn only; usable on low days.
- **Pet peeves and topics that are off limits.** Learn only, when they push back. Memory already has
  a boundary kind for this.
- **How they like affection shown** (words, teasing, attention to what they are into). Ask once,
  much later, as a playful question, never a survey.

## What feeds features that already exist

- **Dates that matter besides a birthday** (anniversaries, exams, holidays they keep). Learn only.
  The reach-out's "on the day" kinds (ADR 0015, 0021) have little to work with without them.
- **The chapter of life they are in** (a job search, a move, a long project). Learn only. Open loops
  catch single plans; this is the larger thread they belong to.
- **How often they want it to reach out.** Today a setting (`COMPANION_REACH`). Once reaching out
  goes live it could ask in the chat ("want me to text you first sometimes?") and set the dial from
  the answer, so a person without a terminal can choose.
- **Their comfort with flirting and intimacy.** Today inferred from how messages read (ADR 0017).
  Asking once, plainly, at the right moment is closer to consent than inferring, and a published
  companion would need it.

## Depth, later

Self-disclosure moves from biographical facts to preferences, then aspirations and values, then
private things; the later layers come only when the relationship and they invite them.

- **Favourites and opinions** (music, games, shows, hot takes): material for banter and for the
  reach-out's "a thought". Mostly learned already.
- **Where they grew up, childhood and family stories:** ask when touched only.
- **What they value and why:** only when they invite it; never asked cold.

## Already handled, do not ask

- **Time zone, schedule, sleep, night shifts:** learned from when they write (`core/rhythm.py`).
- **The people and pets in their life:** names are picked up as they are mentioned (the names
  feature).
- **Age:** ask when touched only; it matters for the floor in ADR 0017, and asking cold feels invasive.

## One mechanism, not a feature each

The memory map (J48, shadow) already labels memories by part of their life and picks the largest gap
to ask about. The items above could become its list of areas, each marked ask, ask when touched or
learn only, so one place decides what to ask and keeps it to one question a day. Its review is due
2026-10-26.

## Where to start if this becomes work

The three with the most effect for the least: the venting preference, nicknames they like and do not
like, and asking about the reach-out dial in the chat once reaching out is live.

## Background

- Self-disclosure deepens over time from neutral topics to feelings and private matters (social
  penetration theory, Altman and Taylor 1973; EBSCO overview of self-disclosure).
- One companion app's onboarding reportedly asks for name, age and interests, then learns the rest
  in conversation (Siècle Digital, 2018).
- Companion apps that remember well keep a name, preferences, hobbies, the people in someone's life
  with their names, and stated goals (2026 overviews of companion memory).
