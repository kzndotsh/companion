# 0023. Threads: one store for what it may bring up, one picker, one budget

**Status:** proposed 2026-10-25. Not built. Asked for by the owner after the brainstorm in
`docs/inbox/2026-10-25-natural-reasons-to-talk.md`, which approved four new hooks: the interrupted
story, weekly rhythms, a topic gone quiet, and milestones and pending outcomes.

## Context

The companion brings things up on its own in several places, each built as its own feature:

- **Open loops** (ADR 0015, `features/openloops/`): plans they mention, stored in `open_loops` with a
  kind (follow up, celebrate, encourage), `follow_up_at`, a sensitivity and a state on
  `open_loop_events` (open, asked, resolved, expired, dropped). One is offered as a note when they
  write (at most one a day, two offers a plan), and in shadow it can be a reason to reach out first.
- **The calendar** (`features/calendar/`): public days, the relationship's dates and lead-ups,
  computed each turn, offered after the history on a casual turn, no repeat within three days.
- **The check-in** after a heavy talk and a gap (`turn/notes.py`).
- **"A thought"** (ADR 0021, `features/reach/`): a reach-out about a memory, one of its tastes or a
  recent episode, picked from a pool and not repeated for 14 days.

Each of the four new hooks has the same shape: a cause in the data, a time it fits, and a life that
ends (answered, outgrown or expired). Built as four more features, each would copy what the existing
ones already copy. A read of the code on 2026-10-25 found:

- The same "once in 24 hours" cap written six times, each with its own decision key, and no shared
  budget for how much it brings up or asks in a day.
- Three ways of saying "a casual turn" (`is_casual` in look-ups, `quiet` in notes, and only "not in a
  scene" in others).
- Three gates for reaching out that have drifted: plan check-ins use fixed quiet hours of 11 PM to
  8 AM while reach-outs use the learned ones (ADR 0021), and a plan's 20-hour gap does not count a
  reach-out sent just before.
- A hand-kept list of notes that ask a question, which had missed two of them (fixed the same day by
  a flag on each note's offer).

## Decision

**A thread is one thing the companion may bring up.** Every source writes threads; one picker
chooses among them; one budget limits them; one lifecycle ends them.

```
Thread
  id, relationship
  source      plan | episode | memory | date | its own (later: promise, question)
  kind        what to do with it: follow up, celebrate, encourage, pick back up, nod to the day,
              ask how it went
  about       the claim in plain words, with the quote and message it came from
  window      from, until: when it fits (a date, a weekday, "after they next write")
  sensitivity 0 to 3; 2 or more is never raised on its own (as today)
  state       open, offered, resolved, expired, dropped (the open-loop states, renamed "asked" to
              "offered" because a nod is not a question)
  offers      how many times it has been offered (at most two, as today)
```

- **Open loops become the first source**, not a separate store: the `open_loops` table and its events
  are generalised (a `source` column; a window instead of only `follow_up_at`), and every existing
  plan keeps its id and history. The ledger never deletes (ADR 0002).
- **New sources only write threads.** Each is a pure rule over data the bot already keeps:
  - *the interrupted story*: an episode (`features/episodes/`) that ended on a goodbye while a topic
    of theirs was still open; window from their next message after a gap, for a few days.
  - *weekly rhythms*: a memory of something they do on a weekday; window that day, every week.
  - *a topic gone quiet*: an upbeat memory thread they raised often that has not come up for two
    weeks; offered once, then dropped.
  - *milestones and pending outcomes*: a dated memory coming round (a month in a new job), or a
    thing they wait on with no date ("any news on…") a few days after they said it.
  A model may label (as the open-loop and episode passes already do); code decides what becomes a
  thread and when, and logs why (ADR 0003, 0014).
- **One picker for a turn.** On a casual turn (one shared test), when no other note asks them
  something, it picks at most one open thread whose window holds, by a fixed order of kinds, and
  offers its note after the history. The thread is marked offered only once the turn is stored, as
  notes already do.
- **One budget.** The picker, not each source, owns "how much a day": at most one thread a day as a
  note, as each feature allows today, counted across sources. The calendar's lead-ups and the
  check-in join the same count when they move over.
- **One gate for reaching out.** A thread may be a reason to text first (ADR 0021) only through the
  reach gate: learned quiet hours, the unanswered rule, the share dial and the needy check, for every
  kind. Plan check-ins move onto it, so the drift above ends.
- **What stays out.** Reminders are things they asked for and must be delivered on time; they keep
  their own store and contract. Look-ups that answer what they just said (relevance, lore, episodes
  shown on "last night", recall) are not threads. Questions about them (basics, the memory map, the
  knowledge hooks) may become a source later, under the same budget, but not in the first step.

## Order of work

1. Generalise open loops into threads with no change in behaviour: same notes, same caps, same
   tests passing, the chaos test passing.
2. Move the picker's casual test and daily budget into one place, and plan check-ins onto the reach
   gate (shadow, so nothing sent changes).
3. Add the interrupted story as the first new source, after counting how often its moment happens
   in the ledger. Shadow first: log the would-offer, judge it by eye.
4. Weekly rhythms, then milestones and pending outcomes, then a topic gone quiet, each counted
   first, shadow first, one at a time.
5. Later, and each by its own decision: the calendar's occasions, "a thought", and its own promises as
   sources.

## Consequences

- A new reason to talk is a source of a few dozen lines: a rule that writes threads. It inherits the
  casual test, the budget, the lifecycle, the reach gate and the logging, so it cannot drift.
- One place decides how often it brings things up, so "too much" or "too little" is one setting to
  measure, not six.
- A migration of a live feature (open loops) comes first, before anything new shows. It must keep
  every past plan readable and the note's behaviour unchanged, checked by the existing tests and a
  replay of past turns.
- Sources compete for one slot a day. Which kind wins is a fixed order in code, to be tuned from what
  is taken up; a thread offered and not taken up is data, not a failure.

## Open questions for the owner

- The daily budget: one thread a day across all sources (as now per feature), or a little more once
  several sources exist.
- ~~The order of kinds.~~ Decided 2026-10-25: when two fit the same turn, the interrupted story
  wins, then their own plan due today, a milestone, a weekly rhythm, a topic gone quiet.
