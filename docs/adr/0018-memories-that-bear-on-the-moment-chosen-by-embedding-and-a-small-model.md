# 0018. Memories that bear on the moment, found by embedding and picked by a small model

**Status:** proposed 2026-10-19. Built in shadow the same day (`core/relevance.py`,
`loops/relevance.py`); live behind a gate since 2026-10-21 (see the update below): `COMPANION_RELEVANCE`
is on unless `shadow` or `off`. Accepted, or changed, once a week of flags on turns that used it is read.

**Context.** The card shows 15 memories a turn, ranked by kind and recency, out of about 135 ordinary ones
(the card's own log, 2026-10-19: "131 current beliefs crowded out, it holds 15" on most recent turns). So
most of what it knows never reaches a reply unless they ask it to remember (the recall look-up, which ran 6
times in about 940 turns). What it knows about their dogs, their beers or a film from their childhood shows
up only if it happens to be recent. Selection, not the size of the card, is the gap.

**Decision.**

- **Each memory's claim is embedded once** (`openai/text-embedding-3-small` through OpenRouter,
  `COMPANION_EMBED_MODEL`), stored unit-length in an append-only table keyed by memory and model. A memory
  with a new claim is a new memory, so nothing is re-embedded in place.
- **On an ordinary turn** (not a scene, the listening judge has read it), their message is embedded on its
  own and together with the companion's last message. The 15 nearest memories are the shortlist.
- **What may be found follows the card's rules, in code.** Only memories stated for real; never a
  crisis-level one; a sensitive (held) memory only on a turn where they share something.
- **A small model picks at most three from the shortlist, or none** (`system/relevance`). Similarity
  alone always returns something and cannot tell a joke from a plan, so the model is allowed to say none.
- **Shadow first.** Each look-up is one logged decision: the nearest three by each query, the picks,
  whether each was already on the card, the time of each step and the cost. It runs beside the turn and
  never holds up or changes the reply.

**Why.** Embeddings make the per-turn search nearly free and fast; a model reading a short list catches
what similarity misses and can answer none. Code keeps the rules about what may be seen, so a better
search can never surface something the card would hold back. Logging whether a pick was already on the
card tells whether the fixed 15 mostly carry the wrong things.

**What decides the next step.** After a few days of the shadow log, a judge from another model family
(a Claude subagent) and the owner read a sample of turns and mark which picks bear on the message. If
the embedding's own top three are about as good as the model's picks, the model call is dropped. If the
picks are good and rarely on the card already, they go into the system block as a short note on that
turn, and callbacks are watched for forced ones. If picks overlap the card a lot, the card is fine as it
is and this stays off.

**Rejected.**
- Raising the card's 15: more text, still chosen without regard to the message.
- Summaries of many memories in one paragraph: model-written text in the card with no quote behind it
  (ADR 0001).
- A memory tool the talker calls while it writes: it changes the talker's contract and makes a turn
  harder to replay. Only if the simple path fails.
- A vector database: about 200 vectors are compared in plain code in a few milliseconds.
- Free embedding models: their terms allow training on what is sent, and these are their memories.

**Reverses if.** The picks are no better than the card's own ranking, or they surface memories at the
wrong moments once live.

## Update, 2026-10-21: live behind a gate

The review of the shadow log found the small model rarely said none and judges disagreed on what counts.
The owner's own marks found no memory "needed" on ordinary turns, but then flagged a turn where the
companion asked how they take an everyday drink; the look-up had picked both memories about it and neither was on the
card. So it runs before the reply, the small model is asked only when the closest memory scores 0.42 or
more (about one turn in five, including those turns), and at most two picks not already on the card
are shown as "may bear on this; never ask what it answers". Measured on that turn: the reply used the
memory 3/10 with the note, 0/10 without. Judged next by the owner's flags.
