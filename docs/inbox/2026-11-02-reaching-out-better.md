# Reaching out better: three designs after nine days in shadow

Added 2026-11-02. Follows the shadow review in `evals/CHANGELOG.md` (2026-11-02, ADR 0021).

## What failed, by cause

- **Hours.** `core/rhythm.py` learns the hours they write, not the hours they start a conversation. Late
  chats that run past midnight made 1 and 2 AM count as usual, so a draft went out at about 3 AM. Also
  `core/clock.py` `local_zone` is a fixed offset, not a named zone, so times from before a DST change
  are an hour off.
- **Right after a heavy chat.** No hold reads the last episode's weight.
- **A dislike used as a like.** Memories carry no stance, and the pick (a hash of the date) cannot tell
  "does not want to watch X" from "loves X".
- **A repeat two days later.** The reuse check keys on id; a memory and its own taste about the same song
  have different ids.
- **About the relationship itself.** One source taste was already about the relationship.
- **Broken text.** The prompt asks for JSON while the call already forces a tool schema, so a small model
  nested JSON in the field; and one draft carried a mis-decoded emoji from the provider.

## Outside

- Inner Thoughts (Liu et al., CHI 2025): a pool of candidate thoughts, each rated on relevance,
  information gap, expected impact, urgency and originality; it speaks only above a bar, and the bar
  drops the longer it has been quiet. https://arxiv.org/html/2501.00383v2
- ProactiveBench (Lu et al., ICLR 2025): a reward model from accept/reject labels agrees with people
  well; false alarms and timing stay hard. https://arxiv.org/pdf/2410.12361
- An audit of six companion apps found guilt and fear-of-missing-out hooks in over a third of goodbyes:
  more engagement, and more sense of being manipulated.
  https://www.library.hbs.edu/working-knowledge/how-ai-chatbots-try-to-keep-you-from-walking-away
- Interruptibility studies: sender, content, time of day and the person's own history predict whether a
  notification is welcome. https://discovery.ucl.ac.uk/1502364/1/CHI16.pdf
- Responsiveness (Reis and Shaver): what builds closeness is the receiver feeling understood, which
  favours something of theirs over something of the sender's.

## Three designs

**A. A thought pool.** Candidate thoughts collect from memory, its tastes and their plans, each resting on
a quote of theirs, with a stance read (three model reads, kept only if all say welcome and not about the
relationship). A reach-out happens when the best thought clears a bar; missing them only lowers the bar.
Repeats blocked by meaning. About 900 new lines. Risk: it starves, the weights are guesses.

**B. Their world first.** Only reach out when something of theirs has ripened: a plan or event just past,
a show, game or project they were in the middle of. Its own tastes and "thinking of you" leave the send
path. Three drafts, a judge picks one or none. About 450 lines. Risk: two or three a week, and it can read
as a tracker.

**C. Keep the gate, close the gaps.** Hours from conversation starts with a night floor; a hold after a
heavy or scene episode; a stance check on the pick; repeats by meaning; the drafter sees the last few
lines; JSON unwrapped and the emoji repaired or dropped; owner marks on drafts; outcomes only ever lower
the dial. About 250 lines. Risk: stance by word list is a patch.

All three agree on: hours from conversation starts, a hold after a heavy chat, a stance check, repeats
by meaning, the two text fixes, and learning that only lowers.

## Recommended merge

C as the base, with two grafts:

1. From A, the stance read by model (three reads, unanimous), not a word list: memories have no field
   for it and a softly worded dislike slips past a regex.
2. From B, their own things first: a project, show or plan of theirs they were in the middle of ranks
   above its own tastes; its own taste only when close in meaning to something they said they like.

Left for later: A's full pool and score. Open question for the owner: with stricter rules the share it
starts will fall below `warm` (1 in 3); whether to accept that or lower the dial.

## How to measure

Replay the nine shadow days through the new gate and pick, for free. Then draft each surviving moment 12
times and judge blind against the old drafts, under a stated cap of cents. Then a week more in shadow.
