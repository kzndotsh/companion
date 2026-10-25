# A cooldown before raising the same memory again

**Status (2026-10-25):** not built; undecided, card G16.

Added 2026-10-18. Undecided; the owner wants to weigh it.

## The idea

Once the companion brings up a memory unprompted, code stops it raising the same one again for a while,
and logs what was surfaced or held back and why. Several companion projects do this with a small ledger
(a "next eligible at" time per memory, or "not again within this session").

## For

- Repeating a callback two days running reads as a script; repetition is one of the top complaints in the
  user research, and spacing makes each callback feel like real recollection.
- A log of what was surfaced and held back makes "why did you bring that up?" answerable.

## Against

- Friends do repeat themselves: asking how a job hunt is going every few days while it is ongoing is
  wanted, and a hard cooldown could suppress that.
- It is not a measured problem yet: there are already rules against asking about answered things, a habit
  check, and a card of about fifteen beliefs a turn. No flag has been about a repeated callback.
- One more rule is one more way to hold back the right memory at the right moment.

## When to revisit

When a flag shows it repeating a memory, or once the callback score (TODO J2) exists and shows repeats.
