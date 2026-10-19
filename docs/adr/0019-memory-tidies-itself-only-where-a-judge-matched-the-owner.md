# 0019. Memory tidies itself only where a judge matched the owner; the rest is the owner's queue

**Status:** proposed 2026-10-19. Built in shadow the same day: `COMPANION_CONSOLIDATE` is shadow unless
`on` or `off`, and in shadow each action is logged and nothing changes. Accepted, or changed, after a week
of the shadow log.

**Context.** Memory fills with clutter. A review of 218 memories on 2026-10-19 found 16 groups of
duplicates, 21 passing moments of one day (one coffee spill was five memories), 8 out of date, 7 habits
stated from one occasion and 1 contradiction. The card shows fifteen memories, so clutter crowds out what
matters. Cleaning by hand works but does not keep up. Published work warns against the obvious fix:
aggressive merging of memories lowered long-term recall sharply in one study (dedup alone did no harm),
and memory rewritten by a model again and again drifts (each pass drops detail and adds false patterns).

**Decision.**

- **The owner's review is the test.** A judge's label is trusted to act on its own only where, on the
  owner's own decisions, it agreed close to always. On 2026-10-19 that held for two things, read by all
  three of three reads (`evals/CHANGELOG.md`):
  - a memory read as a **passing moment**: 24 of 24 were ones the owner retired;
  - two memories read as the **same**: 9 of 10 pairs the owner also found redundant.
- **Only two actions run on their own**, and neither loses a quote:
  - a passing moment that has already faded from the card (ADR-free rule in `core/card.py`: a one-day
    moment of daily life, a week after it was last mentioned) and is not sensitive is closed, reason logged;
  - a new memory the judge reads as the same as an existing one is not stored; its quote becomes
    evidence on the existing memory, the path a restatement already takes.
- **Everything else goes to the owner's queue**: merges, out of date, overstated, replaced and
  contradicting memories, and anything sensitive. A few at a time; the owner answers, and code applies
  the answer through the logged retire and merge paths.
- **Nothing is ever merged automatically,** and a merged memory is never merged again by a model.
  Quotes stay the source of truth (ADR 0001); nothing is deleted (ADR 0002).
- **Shadow first.** For a week each action is logged as what it would have done.

**Why.** The judge is good at the narrow calls and poor at the ones that are really the owner's (what is
out of date, what is overstated): on the seven memories the owner chose to keep, it wanted to retire most.
Letting it act only where it matched the owner keeps the clean-up from deciding what the person is.

**Rejected.**
- Embedding similarity alone as the decision: no cut separates the owner's duplicates from unrelated
  pairs (0.6 catches 25 of 31 and passes 26 others).
- Automatic merging, or a nightly rewrite of memory into summaries: the published results above, and the
  judge merged readily.
- A queue for every memory: a few questions a day, or the queue becomes a chore.

**Reverses if.** The shadow week shows an automatic action the owner would not have taken, or the
queue's questions go unanswered.
