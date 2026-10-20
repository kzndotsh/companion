# 0020. The companion's own lore lives in its views, labelled by kind, and is shown when the moment touches it

**Status:** proposed 2026-10-20. Phase 1 (the labels) and phase 2 (tastes shown, measured, on) built the same day. Accepted, or changed,
once phase 2 is measured.

**Context.** A personality forms from small invented details: what it likes, what it finds funny, a name
it chose. Left loose, those details are said once and forgotten, so tomorrow it may say the opposite. The
views ledger (ADR 0009) already records what the companion says about itself, each with a quote, a check
that it is settled (said on two days), a conflict check against what the user wants, and the owner's
approval. On 2026-10-20 it held 99 such views, but almost none reached the companion: views run in review
mode with 9 approved, and most tastes were said once and never settled. About half of what it records is
not lore at all but advice or an opinion on a topic ("shedding 50 to 100 hairs a day is natural"); the
real lore is a small set (a name it likes, music for a Friday, how it feels about naps, a film). No
invented life event had been recorded, and the persona tells it not to claim a body (ADR 0011).

Research (2020 to 2026): a chatbot that shares about itself drew deeper sharing and was rated more intimate
and enjoyable over a month (CHI 2020, measured), with invented content and the bot's nature known; one
study found companion behaviour lowered trust, so it needs a limit. Personas drift within about eight
rounds (2024, measured); checking a new line against earlier ones cuts contradictions (Dialogue NLI,
DECODE, measured). Nothing measured supports "what I did while you were away", and nothing shows invented
human experiences are accepted.

**Decision.**

1. **One home.** The companion's lore is its views, not a new store. A small judge labels each view with
   one kind: **taste** (what it likes, dislikes, finds funny, a quirk, a name it chose: its lore),
   **stance** (advice or an opinion on a topic), **rule** (how it treats the user: the promise kind, where
   the J12 promise read joins it), **self** (what it is and can do), or **lived** (a claim that something
   happened to it in the world, or about a body or senses). A lived claim is never lore (A22). Models
   label, code decides; the label carries its prompt version.
2. **Shown when the moment touches it.** On an ordinary turn, at most two of its own tastes nearest their
   message (by embedding, like ADR 0018) are shown to it in the system block as its own, settled or
   approved first. Not every turn, and never a list of everything it likes.
3. **Checked before it is kept.** A new taste is read as a pair with its nearest existing taste (the
   memory pair judge, ADR 0019); one read as a contradiction becomes a question for the owner. Nothing it
   said is rewritten.
4. **One thread of its own.** Something it said it wanted to come back to becomes a low-priority open loop
   it may raise on a casual turn, at most daily, framed as what it was thinking about, never as something
   it did. Never at a goodbye or after silence.
5. **The owner reads and prunes it.** `companion lore` lists its tastes with their quotes; a retire goes
   through the logged retire path.

**Why.** The ledger, its quote rule and its gates already exist and work; the gap is that the lore in it
is mixed with advice and never shown back. Labels separate the two, and showing the nearest tastes when a
topic comes up gives consistency where it matters, without a long character bible the model drifts from.
Lore stays its own words, so nothing is invented by code or by a second model.

**Consequences.**
- Phase 1: the kind labels, in shadow (`system/lore-label`, `companion lore`). Phase 2: relevant tastes in
  the system block, measured on a fixture that asks what it likes on different days. Phase 3: the
  consistency check. Phase 4: the thread of its own (J6, small).
- The J12 promise read and the views' promise kind overlap; once both run, one becomes the source.
- Authored tastes in the core persona (R14) wait until phase 2 shows gaps. A character sheet already gives
  an authored past and stays over the persona.
- Not doing: invented off-screen activities, anything about a body or a physical life, lore from a pretend
  scene recorded as real, a free notebook the model writes without a quote, a lore score.

**Reverses if.** Phase 2's fixture shows no gain in consistency, or the owner finds the surfaced tastes
forced.
