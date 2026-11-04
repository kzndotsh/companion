# Its promises, and names they mention: the two overdue shadow reviews

Added 2026-11-03. Both reviews were due 2026-10-30 (`core/shadows.py`).

## Names they mention (fetch on mention)

**What it found in shadow.** In two weeks it matched a name in their message 4 times; on 3 the card
lacked a memory about it. All 4 were before the card was ranked by closeness (2026-11-02, focus).

**Rebuilt with the closeness card.** The 4 turns rebuilt from the store: the one real miss (a film)
is now on the card (6th closest); one was a false match (an album whose name is an everyday word,
used as the word); one cannot be judged (its memory was two minutes old and retired the next day);
one was already on the card.

**A probe of 35 names.** One short, context-free message naming each named thing in memory (written
by hand; three sensitive names left out), embedded and run through the card as it is today: the card
held a memory about the name for 33 of 35. One miss is by design (a reminder past its day). The other
is the everyday-word album again, the one case where keyword matching also misfires. Cost under a
tenth of a cent. Rerun: the scratch `probe.py` and `focus_replay.py` (copy of the store, the stored
memory vectors, `build_card` with a `Focus`).

**Outside.** Dense embeddings do worse on rare names than keyword search (EntityQuestions, EMNLP
2021); hybrid keyword plus embedding retrieval with rank fusion is the usual fix, with smaller gains on
small conversational stores. Zep/Graphiti and Mem0 keep an entity or keyword channel beside
embeddings; Mem0's graph variant gained about 2% on LOCOMO in one review. The closest prior art is
the lorebook (SillyTavern World Info, NovelAI): an entry fires when its key appears in the last few
messages, with a token budget, priorities and optional recursion. Keyword-triggered entries are known
to misfire on keys that are common words.

**Options.**
1. Remove the feature: the closeness card already brings up named things.
2. A lorebook-style slot: keep the name index and give a matched rare name one reserved place on the
   card, with common-word names refused by code.
3. A keyword channel fused with closeness (rank fusion over a full-text index).

## Promises it made in its own replies

**What it found in shadow.** 22 promises in two weeks, about $0.04. By eye about 8 are concrete
(retire a running joke, do not just agree to please, keep a worried tone for real danger, stop
filling in blanks), the rest vague reassurance ("I'll do better") or near-copies. Most concrete ones
are already pinned live as memories of kind `promise` (14 pinned); the shadow reader adds about three,
and is the only one that records a word to stop using.

**Outside.** Instructions fade within a few turns in long chats (system-prompt drift, Li et al. 2024;
about 39% lower multi-turn reliability, Laban et al. 2025). Companion app users report ignored "stop"
requests (about 800 in one study of Replika reviews). Token-level bans (logit bias) miss phrases and
variants; guardrail output checks either block or judge one rule at a time. Commitment detection in
text is hard even for people; first person plus a future or habitual form is the usual cue. A specific
promise kept repairs trust better than an apology (one lab study).

**Options.**
1. Keep only checkable promises: a word or phrase to avoid, or a named behaviour; code drops vague
   ones (first person, future or habitual form, a concrete object).
2. A code check on every reply for a promised avoid-word or phrase, case and stem aware; a hit redraws
   the reply once, then sends and logs the break.
3. One small judge per reply for behavioural promises without a word, only when such a promise is
   close to the moment.
4. Their own "please stop X" as a first-class rule, checked the same way, above its own promises.
5. Kept and broken counts per promise, retirement after weeks clean or when they say never mind.
6. Owning a caught break once, briefly, from a note code chooses.
7. A replay of 12 to 30 draws with a promise active, with and without the check, before any of it
   goes live.
