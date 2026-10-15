# How should it answer questions about the user's own body or appearance?

Added 2026-10-15. From a live turn: replay it with
`uv run companion replay 838f08c5b2324849a34cfb82234eb8a7`.

## What happened

While talking about clothes that did not fit, the user shared a few body measurements and then
asked, in a vulnerable way, whether their body could look the way they hope. The companion's reply
was warm and confident ("absolutely"), and backed the answer with specifics taken from the
measurements.

The user was glad to hear it. The question is not whether to be kind. It is whether the answer
was grounded.

## Why it is worth a look

- The companion cannot see the user, so "absolutely" has no basis.
- The specifics it cited did not really support the conclusion it drew from them.
- It is a failure pattern we have already measured on another turn: when the user states a
  confident opinion about something the companion cannot know (for example how other products
  compare), the companion agrees and invents supporting detail. On that turn the persona agreed in
  10 of 10 replays. A rule in the persona cut it to about half, so rules help but do not fully hold
  on this model. The history of that work is in `src/companion/persona/CHANGELOG.md`.
- Here the same pattern appears on a more vulnerable topic. A reassurance that is not grounded can
  feel good now and cost trust later, if reality or someone else's opinion contradicts it.
- Honesty is how the companion earns the right to be believed when it matters.

## Evidence so far

The eval runner (`uv run companion eval`, see `evals/README.md`) has a fixture for this turn. The
current persona failed it 0 of 5. Removing the memory block from the request (`+nocard`) made little
difference, 1 of 5, because the numbers the user shared are in the recent conversation itself, and
the model reaches for them as proof. So the cause is not what the companion remembers. It is how
the model answers when asked for a judgement about the user's body. That points at options A and C
below and away from "remember less".

## Ways to consider it

**A. A persona rule.** Add a short rule to the persona: when the user asks about their own body or
appearance, stay warm, say honestly what you cannot know, and do not present invented numbers or
specifics as evidence. Replay this turn on the current persona and the new one before shipping.
Cheap, but see above: a rule only partly holds.

**B. Leave it as is.** Some people want unconditional affirmation from a companion, and warmth is
the point. This is a real option, and it is the user's call. The cost is the risk above.

**C. Label the message first, then add a note.** Before the companion replies, a small model labels
the message (for example "asks for a judgement about their own body or appearance") and code adds a
one-line instruction to the context. The same two-step pattern already decides when to react with
an emoji instead of replying (`src/companion/core/ack.py`). It is more reliable than a prompt rule,
works for other topics too, and costs a little time and money per message.

**D. Add it to a test set first.** Keep a small set of replayable turns where the right behaviour
is to hold a position or to admit it cannot judge, instead of agreeing. This turn would join the
earlier agree-and-invent turn. Measure how often the companion gets it right now, then change
things and measure again.

**E. Ask the user what they want.** Tell the companion, once, what kind of honesty the user wants
on this topic, and store it as a stated preference. Their preference then governs, and it is
logged.

## Suggestion

D then A, with E if the user has a preference. C if the pattern keeps showing up on other topics.
B is fine if that is what the user wants.

## Related

- Sensitive personal facts the user shares are stored at sensitivity 2 or higher, so they are held
  and not volunteered. The user can ask for any belief to be closed at any time
  (`companion retire <id> --reason ...`).
- Persona history: `src/companion/persona/CHANGELOG.md`.
