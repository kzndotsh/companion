# 0024. What they said is coming is tracked until it happens

**Status:** accepted 2026-10-25 by the owner. Built in shadow (`COMPANION_NOW`), review by 2026-11-08.

## Context

A flagged turn: they said dinner was coming soon, the chat went on about the food, and two minutes
later the reply asked how one of the rolls tasted. Replayed on the live talker, about 1 reply in 6
did this. The persona already says not to assume something they were about to do has happened, and
the clock line already gives the time; neither stopped it. Measured on that turn (`evals/CHANGELOG.md`,
2026-10-25):

- Giving the talker the exact seconds since their last message, or how long the stretch of chat had
  run, changed nothing (within noise). A 2025 study of agents' sense of time found timestamps help only
  a little.
- A note telling it to treat dinner as still to come stopped the slip (0 of 120) but turned 43 of 120
  replies into a send-off that winds the chat down.
- The same fact on the card, in the system block, did nothing (10 of 60).
- A check after the reply caught 23 of 24 slips but flagged 70 of 296 good replies.
- A line after the history that only states the fact, "About two minutes ago they said dinner is
  coming soon. It has not come yet unless they say so.", cut the slip from 20 of 140 to 8 of 150 (a
  real difference) with no rise in send-offs.

In the real history, about one message a day says they are about to do something (eat, shower, sleep,
coffee, laundry). The talker cannot infer from the history alone which of those has happened, so the
fix is state the code keeps, not another rule for the model.

## Decision

**One reader of what is happening with them now.** The stepping-away reader that fed nudges
(`system/away`) becomes a reader of their now (`system/now`): beside each real, not serious turn, a
small model labels their message as one of `soon` (something of theirs is about to happen, and they
are still here), `leaving` (they are going now and will be away), `back` (they are back), `done` (the
thing they said was coming has happened) or `none`, with a short phrase for what and the minutes it
likely takes. It runs whether or not reaching out is on, since the note is in the chat. One reader,
not a second one beside the old: the old reader's job is a case of the new one.

**Code keeps the state.** Each label is a decision (key `now: what is happening with them`). What is
open now is a fold over the last few hours of them, newest last: a `soon` or `leaving` opens an item;
`back` or `done` closes everything open before it; an item also closes once well past its time (three
times its minutes, at least 20 minutes and at most 3 hours), when it has most likely happened.

**The note states the fact and nothing else.** While a `soon` item is open and they are still
chatting, the line after the history says how long ago they said it and that it has not happened
unless they say so (`notes/now-soon`), the wording measured above. A `leaving` item needs no note: if
they are writing, they are back. Nudges read the open `leaving` item instead of the old reader's
decisions.

**Shadow first.** In shadow the reader and the state run and the note is logged as it would be sent,
never sent; nudges read the state either way.

## Consequences

- The reply to the message that says it is coming is not covered: the reader runs beside that turn.
  The persona handles that case well (30 of 30 on the sign-off fixture).
- `what` is a model's short phrase in a code-chosen note, as a plan's claim is in the plan notes.
- The same state can later tell the companion they are at work, out, or eating, if flags show the need.
- The old reader's prompt stays as a retired version; its decisions are no longer written.
