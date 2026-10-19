# 0003. Every choice is a decision with a reason, including doing nothing

**Status:** accepted 2026-10-15. Records a decision already built (commit 1ea1198, extended since).

## Decision

Whenever the companion chooses to surface something, hold something back, start a conversation,
stay silent, or apply a policy, it appends a `Decision` row.

- The kinds are `surface`, `withhold`, `initiate`, `do_nothing` and `policy`.
- A decision must carry a non-empty reason.
- It carries a belief id exactly when it surfaces or withholds one.
- It also has a turn and a trace id, and a JSON `detail` for scores and context.
- Decisions are append-only (ADR 0002).

Silence is a decision. Declining to reply, or to raise something, is logged the same way as
speaking.

## Why

- Most memory systems log what they retrieved. Whether a companion is appropriate depends on what
  it chose not to say, and a log of only the things it said cannot show that.
- Keyword checks on reply text cannot tell a natural callback from an announcement, or a sensible
  surfacing from an intrusive one. The decision log can, and it is the artefact evals should read.
- With a reason on every row, a bad behaviour can be traced to a rule or a score instead of
  guessed at.

## Consequences

- When written, the log recorded each belief's placement in the state card (`surface` or, for
  sensitive beliefs, `withhold`), each acknowledgement judgement (react or reply), belief
  acceptances, rejections and closures, and a policy row for every reply.
- Since 2026-10-19: more choices write rows (frame, listening, recall, quips, open loops, views
  and others, mostly as `policy`). `initiate` and `do_nothing` are now used by the initiative
  gate, which runs in shadow mode (`would send`, nothing sent; ADR 0015). The card is still not a
  priced bid.
- ADR 0006 adds the rule that the reason is written by code from the recorded scores, never by a
  model.

## Reverses if

The volume of decision rows becomes a real cost. The answer would be to sample or aggregate
low-value ones, not to stop recording reasons.
