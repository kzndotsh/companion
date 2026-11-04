# Ideas from an emotion simulation workbench

From a public emotion simulator for game characters (sim.foxengine.ai, "Emo" v2), read 2026-11-04.
It runs a small cast through a day: 54 feeling and need channels, events described by appraisal
(valence, novelty, humor, threat, loss, rivalry, attachment and 20 more), per-feeling half-lives,
directed liking and trust between characters, and a timetable for each one. Its own notes say the
numbers are authored assumptions, not validated psychology.

## What it confirms

Our mood (ADR 0016, `features/mood`) is the same shape at a smaller size: effects with an amount, a
half-life and a cap, added up per state, owned by code. Their 54 channels show why we kept three: a
model shown a dozen numbers recites them, and nobody can tune that many by hand.

## Worth noting

1. **A feeling needs its cause, not just a mood.** Their rules: amusement needs a humor appraisal
   (novelty alone is not enough); jealousy needs a perceived rival and a valued bond. For us: a
   character sheet that is possessive should show jealousy only when they mention a real rival, never
   as a pull when they are busy or quiet. Users of another companion service named exactly that as
   the thing that made them stop (`docs/inbox/2026-11-04-their-standing-requests-about-how-it-talks.md`
   source). Check before building: count replies that show jealousy, and what came before each.
2. **How long a feeling lasts depends on how much it mattered** (Verduyn and Lavrijsen 2015: duration
   varies with importance and rumination, not a fixed half-life). Our `serious` source lasts 12 hours
   whether the read was 2 or 3. An acute read could last longer than a serious one.
3. **Anticipation before a known event.** Their events can rise before they peak. We already keep
   what they said is coming (ADR 0024, `now`, shadow): a light "looking forward to it for you" warmth
   before their thing could come from the same record, ending when it happens.
4. **A day of its own.** Each character has a timetable, so "what are you doing" has one answer for
   the whole afternoon. Ours makes up its day per reply; its own history (ADR 0025) keeps its past
   straight but not its present. A code-owned rough day (morning, afternoon, evening) would keep it
   consistent across a chat, with LR4. Measure first: how often it says two different things about its
   own day within a few hours.

## Not for us

Needs like hunger and sleep for the companion, many-character relationship tables, and the full 54
channels.
