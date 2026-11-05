# The card does not follow the topic

Added 2026-11-02.

## What was noticed

An audit of 150 turns sampled from the 371 since 2026-10-25 (five Haiku readers, each turn with its
card, the relevance note's picks, the nearest memories and the recent history) found about 160
problems with which memories the talker was shown: about 46 unrelated memories, 44 duplicates or
wrong memories, 40 missing ones, 15 misused in the reply and 14 out of date.

## What was measured

From the store, the same 371 turns:

- The main memory list held 80 distinct memories across all 371 cards, of about 245 current ones.
  The four memories of kind `boundary` were on every card. The most frequent ordinary memories were on
  250 to 273 cards each, whatever the topic. `card: N current beliefs crowded out` said 110 to 215 each
  turn.
- The relevance note's gate (0.42, `features/recall/logic.py`) skipped the pick on 218 of 266
  look-ups (82%). Memories that bore on the message often scored 0.30 to 0.40. It does not run on a
  turn the roleplay talker answers.
- One fact is often stored several times: three wordings of one film habit, five of one event, eight
  lines from one conversation about what they want in a partner, pairs for one meal or one project.
  On some cards about 7 of the 15 places were distinct facts.
- Two settings are stored as `boundary` (play restrictions off, stay in the romantic framing), so they
  sort first on every card, scenes included. Two more boundaries are dated requests that may no
  longer hold.
- Facts about one day (a plan for that day, having just woken up, a meal, a reminder already sent)
  stayed on the card two to four days.
- On a turn that is not casual every held memory is shown, related or not: dosing and private
  habits sat on a morning greeting and on a crisis turn. Errands and shopping sat on intimate scene
  cards.
- Some memories are wrong: a feature being built for the bot stored as a fact about the user, a
  wondering stored as a diagnosis, one evening generalised to a living situation.

Side finding: the guess note's `$about` slot is filled with model text (`notes/guess`), and one turn
sent it cut off mid-sentence. Notes are chosen by code, not written by a model (ADR 0014).

## A first check of option 1

The 150 sampled cards rebuilt from the store at each turn's time, as sent and topic-ranked (the six
boundaries fixed, ten places by closeness to their message and to the reply before it with it, a
memory within 0.90 of one already chosen skipped, held memories only at 0.40 or closer). The
topic-ranked lists held 170 distinct memories across the turns against 101. Three blind Claude
Sonnet judges, 50 turns each, the two lists shuffled, asked which list would better help a reply to
that message: topic-ranked 131, as sent 8, tie 11 (44/3/3, 45/2/3, 42/3/5). This judges the lists,
not replies. The judges' notes: the topic lists carried the fact the message touched and, in scenes,
what they like rather than errands; both still led with the same boundaries; the topic lists still
pulled some sensitive memories below the held level onto unrelated turns (a past heartbreak, a dark
documentary, body measurements), and on very short messages they reached for loose matches.

## Outside

- Letta (MemGPT) keeps a small core block always in view (name, role, preferences, goals, about 2k
  characters) and searches everything else by topic.
- Generative Agents ranks memories by recency, importance and closeness to the query, summed. The card
  uses kind and recency, not closeness.
- Retrieval studies: a strict similarity threshold collapses retrieval toward none; top few with a low
  floor is the common setup; top-k on chat history returns near-copies unless diversified.
- Mem0 decides at write time whether a new memory adds, updates, deletes or is already known.
- Zep / Graphiti gives each fact a valid-from and valid-until; a newer fact closes an older one
  without deleting it.
- CIMemories (ICLR 2026): memory assistants move sensitive details into the wrong context, more so
  as they know more. Rules per context, not one switch.
- OP-Bench: every memory system tested overused memories, about half by repetition.

## Options, best first

1. **A topic-ranked card.** Keep boundaries and basics fixed (about 5). Fill the other places by
   closeness to their message and the reply before it, skipping a memory too close to one already
   chosen, with held memories only above a floor. The vectors already exist for the relevance note.
2. **Day-scoped facts end with their day,** and a reminder's memory ends once it is sent, as a
   valid-until, not a deletion.
3. **Settings out of `boundary`.** Play settings belong with the scene sheet, not first on every card.
4. **The scene memory lane live** (ADR 0026, in shadow until 2026-11-09): today's scene cards carry
   errands and shopping.
5. **Already known at write time,** as Mem0 does. Bigger, and needs its own measurement.

## How to rerun

A scratch script rebuilds each sampled card from the store at the turn's time (beliefs current then,
their stored vectors, the message and the reply before it embedded once, about $0.0002 for 150
turns), both as sent and topic-ranked, and blind judges compare the two lists per turn.
