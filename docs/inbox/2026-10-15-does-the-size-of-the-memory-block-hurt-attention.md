# Does the size of the memory block make the companion worse at following the last message?

Added 2026-10-15. A hypothesis from two measurements. Nothing is decided.

## What the memory block is

Every user message the companion receives starts with a clock line and a memory block: what it
remembers about the user, what it knows but should not raise, older things that may be out of date,
and views of its own. On a recent turn that was about 19 lines, roughly 700 tokens, sitting directly
above the one or two lines the user actually typed.

## What was measured

The eval runner (`uv run companion eval`, see `evals/README.md`) can replay a recorded turn with the
memory block removed (`+nocard`). Two fixtures, 5 samples each:

- a vulnerable question about the user's own body: 0/5 with the memory block, 1/5 without.
- a turn-taking game where the user had just answered the companion's question and the companion
  asked the same question again: 3/5 with the block, 5/5 without.

Both gaps are small and neither is significant at this sample size. In the first, the cause turned
out to be the conversation history, not the block. But the direction is the same twice.

## The hypothesis

A long block placed immediately before the user's words competes with them. The model answers the
conversation's shape (whose turn it is, what was just asked) less well when a wall of facts about the
user sits between it and the latest message. If so, remembering more could make the companion worse
at listening, which would be a real cost of the memory approach.

## Ways to consider it

**A. Measure properly first.** 12 or more samples per variant on these two fixtures and a few
others, with and without the block. About 15 cents. If the gap holds, it matters. If not, drop it.

**B. Put the user's message first.** Keep the block, but order it so the latest message comes before
the memory and a clear marker separates them. Cheap to try and test.

**C. Send less.** Cap the block, drop low-value items (a one-off errand), and show only what is
relevant to the current message instead of everything. More work, but it also lowers cost per turn.

**D. Move memory out of the user message.** Put the block in a separate earlier message so the user's
turn stays clean. Needs a check that the cache behaviour does not get worse.

**E. Accept it.** If the effect is real but small, the benefit of remembering may outweigh it.

## Suggestion

A first, because everything else depends on whether the effect is real. Then B, which is nearly free
to test, before any larger change.

## Related

- `docs/inbox/2026-10-15-body-and-appearance-questions.md`, which has the first of the two
  measurements and a different explanation for it.
