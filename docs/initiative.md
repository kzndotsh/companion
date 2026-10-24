# Plans, reach-outs and nudges

How the companion notices what the person has coming up, and what it would do with it. Everything
that would send a message unprompted runs in shadow for now: it drafts and records what it would have
sent, and sends nothing. `uv run companion initiative` shows what it would have done, and
`uv run companion shadows` shows when each part is due for review.

## Two ways to bring something up

There are two ways it can bring up something the person mentioned:

- **In the chat, when they next write.** A plan of theirs that is due can be offered to the talker as
  a note on a casual turn, so the companion asks about it naturally. This is live, and it is part of
  open loops.
- **Unprompted, by reaching out.** A tick every 15 minutes decides whether to send a message first.
  This is shadow only, behind `COMPANION_INITIATIVE` (`shadow` or `off`).

The two never double up. A plan brought up in the chat is marked asked, so it is never also a
reach-out.

## What can be reached out about

Open loops are things they said about their own near future: a firm plan, an event, something they
are waiting on. A loop is closed when they settle it themselves, and a pure gate decides when it is
due. How loops are read, timed and closed is in `src/companion/features/openloops/README.md` (ADR
0015).

Nudges are for when they said they were stepping away ("brb", "shower time") and then stayed gone
much longer than that. The tick drafts one light nudge. See `src/companion/features/nudges/README.md`.

## The caps every reach-out keeps

Both kinds keep the same caps (`core/reachout.py`):

- never in quiet hours (23:00 to 08:00 local)
- never while they are mid-chat
- at most one plan reach-out a day, at least 20 hours apart
- after one unanswered reach-out it waits 72 hours, and after two it waits for them to write first

A drafted reach-out must be short (18 words at most, or a short question taken from its first
sentence). Nudges add their own limits on top, such as at most two a day.

## Related

The promises the companion makes in its own replies are read in the same batch as open loops, in
shadow (`src/companion/features/promises/README.md`). Reminders they ask for are a separate, live
feature (`src/companion/features/reminders/README.md`).
