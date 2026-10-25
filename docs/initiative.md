# Plans, reach-outs and nudges

How the companion notices what the person has coming up, and when it would write first. Everything
that would send a message unprompted runs in shadow for now: it drafts and records what it would have
sent, and sends nothing. `uv run companion initiative` shows what it would have done, and
`uv run companion shadows` shows when each part is due for review.

## Two ways to bring something up

A plan of theirs that is due can be offered to the talker as a note on a casual turn, so the
companion asks about it naturally when they next write. This is live, and it is part of open loops.
The calendar (`src/companion/features/calendar/README.md`) reaches the chat the same way and only
that way: an occasion is a note after the history on a casual turn (`docs/turn.md`). "A day" as a
reason to write first is planned (phase 3 of the calendar plan) and not built.

Everything else is reaching out: a tick every 15 minutes decides whether to send a message first,
and skips that look entirely once the daily spend cap is reached.
This is shadow only, behind `COMPANION_INITIATIVE` (`shadow` or `off`). `off` stops the whole tick and
also the read of whether they stepped away, which only feeds nudges; the note in the chat is not
affected. The two never double up: a plan brought up in the chat is marked asked, so it is never also
a reach-out.

## Why it would write first

People who like each other write first because something made them think of the other, because it is
the time they usually talk, or because they miss them (ADR 0021). Code chooses the reason, the moment
and the one thing a message is about; a model only writes the words, after every check has passed.
There are five reasons, and when several apply the first in this order is the one it acts on:

- **A plan of theirs.** A firm plan, appointment or occasion they mentioned falls due. How plans are
  read, timed and closed is in `src/companion/features/threads/README.md` (ADR 0015).
- **Stepping away.** They said "brb" or "shower time" and stayed gone much longer than that, so one
  light nudge. See `src/companion/features/nudges/README.md`.
- **A time they keep.** They wrote within the same hour on most of the last week, say first thing in
  the morning, so now and then it is the one to say hi at that hour.
- **A thought.** Something it knows comes to mind: a thread or a like of theirs from memory that is not
  sensitive, one of its own tastes (ADR 0020), or a line from a recent stretch of chat. Code picks it
  the same way for the same day, so a replay gives the same answer.
- **Missing them.** The pause since they last wrote is longer than their usual pause, and it is an
  hour they usually write.

Every reason is weighed on every tick and logged with why it applied or not. How the last three work
is in `src/companion/features/reach/README.md`.

## Their rhythm

"Usual" is learned from when they write, not fixed. From the last two weeks of their messages, code
works out their pauses between conversations (a new one starts after two hours of quiet), the hours
they write, and the hours they almost never write. Before there is history it uses a baseline of a
12-hour pause and waking hours from 9 AM to 10 PM. The baseline gives way to their own numbers as it
sees more conversations, fully from twenty, so a few odd days early on cannot swing it. Someone who
works nights gets quiet hours in the day. Missing them never starts before eight hours, whatever the
data says. The numbers, and how much of them is still the baseline, go with every decision and are
shown by `companion initiative`.

## How often

The dial is a share, not a count: `COMPANION_REACH` says what share of the conversations over the last
two weeks it may start. `rare` is about one in eight, `light` one in five, `normal` one in four, `warm`
one in three (the default) and `clingy` one in two; `off` stops these reasons and plan check-ins
(they ask the same gate, ADR 0023), and leaves nudges as they are. Its own messages are at least six hours apart. In shadow a message it would have
sent counts as a conversation it started, so shadow paces itself the way live would.

Inside the dial it follows how they answer. When its last message was answered later than their usual
pause, or in a few words, the dial steps down one level until they start a conversation themselves.

## What it never does

These are rules in code, checked before and after the draft, not requests in a prompt. They bind
its own reasons and, since ADR 0023, plan check-ins, which ask the same gate (`features/reach/gate.py`
`hold`, through `holds` in `features/reach/run.py`); nudges keep their own caps (below), and share the
crisis hold and the spend cap:

- never in their quiet hours, never mid-chat (any message in the last 90 minutes), never during a
  pretend scene, and a mood never triggers one (ADR 0016)
- never a second message while the last one is unanswered: it waits for them to write first
- never a sensitive memory, and one specific thing per message, kept whole however long it runs (the prompt asks for a short one;
  code never cuts it)
- never guilt, need or blame: a draft that mentions waiting, being forgotten or ignored, how long they
  were gone, asks why they went quiet or whether they are okay, adds urgency or a cliffhanger, or makes
  them responsible for how it feels is dropped, never rewritten
- never a paid call before every cheap check has passed, and none once the daily spend cap is reached
- never within a day of a turn the crisis path read as a concern or a risk and acted on: the plan,
  nudge and own-reason gates all hold (`core/crisis.py` `reach_held`, ADR 0022). In shadow the crisis
  path only logs, and nothing holds
- never counting streaks or optimising how often they write

Nudges keep their own caps as before (`core/reachout.py`): at most twice a day, inside fixed quiet hours
of 23:00 to 08:00. Plan check-ins no longer have caps of their own: they wait on the same gate as its own
reasons, so they use the learned quiet hours, wait while its last of any kind is unanswered, keep six
hours from its last of any kind, and count toward the share. The needy check on the draft still binds
only its own reasons. Nudges and plan check-ins count toward the six-hour gap, the unanswered rule and
the share above.

## Related

The promises the companion makes in its own replies are read in the same batch as open loops, in
shadow (`src/companion/features/promises/README.md`). Reminders they ask for are a separate, live
feature (`src/companion/features/reminders/README.md`), checked every minute rather than on the
15-minute tick, so one lands within a minute of its time.
