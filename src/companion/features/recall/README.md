# Recall

The memories a reply gets beyond the card, by trigger. The card holds only 15 memories a turn out of well over a hundred, so most of what it knows never reaches a reply otherwise. Two triggers bring more: **asked**, when they ask it to remember something or say it forgot, and **near**, the relevance look-up (ADR 0018), when a memory bears on what they just said.

**Status:** live. Asked has no switch. Near is `COMPANION_RELEVANCE`: `on` (default), `shadow` or `off`. Both run before the reply, and their notes go in the system block.

## How it works

### One rule for both

What a trigger may find (`eligible` in `logic.py`): memories stated for real, and never the intimate lane, whatever `COMPANION_INTIMATE_MEMORY` says (2026-11-07) (the roleplay card shows it on a roleplay turn instead, ADR 0026). Asked reaches anything they said, crisis level included, since they asked for it. Near never reaches crisis level, and held (sensitive) memories only on a turn where they share something, the same rule as the card.

What is shown (`extras`): a near pick already on the card, or already shown by the asked note that turn, is not offered again.

### Asked

The listening read labels a request to remember and guesses its topic. In a scene, where listening does not run, the route's read is used (`scene_read`). A small model (`system/recall`, 3 s limit) reads the topic, the last six messages of the conversation (both sides) and every eligible memory, each with how long ago it was said, and points at the ones meant, at most five; code keeps only labels it showed (`core/recall.py`, `kit/recall.py`, whose search the guess shares). The picks go in `notes/recall`, or `notes/recall-empty` when nothing was found, so the reply owns the gap instead of guessing. In a scene an empty look-up adds nothing, since what they mean is most likely in the story itself. Each look-up is logged as `recall`, with the topic and the picks.

### Near


Each memory's claim is embedded once (`COMPANION_EMBED_MODEL`, default `openai/text-embedding-3-small`) and stored, keyed by memory and model. Missing vectors are filled at the start of a look-up (`kit/embed.py`).

On a turn, their message is embedded alone and together with the companion's last reply. The 15 nearest memories to the second query are the shortlist. The pool is limited by code to the card's rules: real-frame memories (stated, inferred or third-party), never crisis-level (sensitivity above 2), and held (sensitive) memories only on a turn where they share something.

The look-up is skipped when their turn is not in the real frame (a scene), when there is no embedder or judge, and when listening is off and there is no listening read. A failed listening read still runs it, as a turn that is not sharing.

Live (`on`): a small model is asked only when the closest memory scores at least 0.42, about 1 turn in 5. Below that the pick is skipped. It picks at most 3 from the shortlist, or none. The whole look-up has a 3 s limit, and a slow or failed one only means no memories are offered. At most 2 picks that are not already on the card reach the talker in `notes/relevant`. The note sits after recall and before recent times. Each look-up is logged as `relevance: what it was shown`, with the 3 nearest memories by each query (`LOGGED_NEAREST`; only the picks reach the talker), the picks, whether each was on the card, timings, cost, models and whether the pick was gated or failed.

Shadow: the same look-up beside the turn with a 10 s limit and no gate, logged as `relevance: what it would have kept in mind (shadow)` with the card's memories marked. It never changes a reply. `off` stops both.

A failure logs a warning and adds nothing.

## Files

| File | What |
|---|---|
| `logic.py` | pure: which memories each trigger may find (`eligible`), which near picks are shown (`extras`), near's gate, limits, prompt and parsing |
| `run.py` | effects: the asked look-up and note (`RECALL`), the near look-up (`look_up`, `shadow`), its note and shadow step (`RELEVANCE`) |

## Prompts

- `system/recall`: the asked look-up; picks the memories they mean, at most five. Unreadable or late means nothing added.
- `notes/recall`: the memories they asked about.
- `notes/recall-empty`: the look-up found nothing; say so plainly, never guess.
- `system/relevance`: picks memories from the shortlist that bear on the message, or none. Unreadable means no picks that turn, and the nearest are still logged.
- `notes/relevant`: the line that offers the picked memories. It goes in the system block.

## Commands

None.

## Measured

- 2026-10-29: "the serious stuff we talked about early" was guessed as the wrong topic and found the wrong memories in 12 of 12 reads; with the conversation and the most sensitive memories, the asked look-up found the one meant in 34 of 34 (`core/recall.py`).
- 2026-11-05, from the decision log: of 17 asked turns, 16 also ran near, and on 5 the same memory was sent in both notes; on 2 everyday turns the asked look-up showed a memory the card had left off as intimate. Both led to the one rule above.
- 2026-10-19: first run on three invented messages. Embedding found the right memories, and a bare "lol ok" still got two picks. About $0.00014 a turn (`evals/CHANGELOG.md`).
- 2026-10-21: two days of shadow logs, 159 turns. Picks bore on the message 28% of the time, against 19% for the embedding's top three with context and 11% for the message alone. 12% of picks were already on the card (`evals/CHANGELOG.md`).
- 2026-10-21: a v2 picker that says none more often was 79% useful against 63%, but two judges disagreed badly. Not shipped (`evals/CHANGELOG.md`).
- 2026-10-21: live behind the 0.42 gate. On a recorded turn it used what it knew 3/10 with the note against 0/10 without, within noise (`evals/CHANGELOG.md`).
- 2026-10-23: logs showed 10% of the three memories closest to each message were on the card (69 of 660). Filling 7 of 15 card slots by closeness did not help: near memories brought up 4/96 against 6/96 today, none-near 2/60 against 0/60, on 26 recorded turns (gpt-6-luna, plain persona). Not shipped. Letting it add 4 memories instead of 2 changes little (1.0 added a turn against 0.8), since it seldom picks more than two (`evals/CHANGELOG.md`).

## Tests

`tests/features/recall/` (`test_asked.py` runs whole turns)
