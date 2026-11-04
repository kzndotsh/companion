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

## What its eight sources say (read 2026-11-04)

Abstracts for six; the full text, partly, for Cowen and Keltner and for Oaten et al. What each found,
then what it could mean for us (a guess until measured).

- **Cowen and Keltner 2017** (PNAS 114(38); 2,185 short videos, 324,066 judgments by US raters on
  Mechanical Turk). Self-report holds about 27 distinct kinds of feeling, and the kinds explain reports
  better than pleasant-unpleasant and calm-excited alone. The edges between neighbours are gradients
  (anxiety to fear to horror; calm to aesthetic appreciation to awe). Some proposed kinds had no
  dimension of their own (pride and triumph went with admiration; contempt and disappointment with
  anger). Limits: US raters, English words, videos only. *For us:* a few named states (our cozy, tender,
  playful) is a sound shape; neighbouring states should blend rather than switch.
- **Smith and Ellsworth 1985** (J Pers Soc Psychol; people recalled experiences of 15 emotions and
  rated them). Six dimensions separate emotions: pleasantness, anticipated effort, certainty, attention,
  who is responsible (self or other), and how much the situation is in control. *For us:* a judge could
  label these about their message (who is to blame, how sure, how much effort ahead) and code pick the
  note, as ADR 0014 already does for severity. One more label, so measure what it changes first.
- **Verduyn and Lavrijsen 2015** (Motivation and Emotion; people recalled recent episodes of 27
  emotions with their duration). Sadness lasted longest; shame, surprise, fear, disgust, boredom, being
  touched, irritation and relief were among the shortest. How important the event was and how much the
  person ruminated explained almost half the difference in duration, holding across definitions and
  after intensity and recency. *For us:* idea 2 stands: a tender mood after something that mattered
  should outlast one after a small thing, and the sweet, touched kind of warmth should be short.
- **Larsen, McGraw and Cacioppo 2001** (J Pers Soc Psychol). Most people in ordinary moments felt
  happy or sad, but many felt both right after a bittersweet film, moving out of their dorm or
  graduating. *For us:* our mood already shows up to two states; a bittersweet message of theirs (a
  goodbye, a last day, an ending they wanted) should be allowed both, not forced to one tone.
- **McGraw and Warren 2010** (Psychological Science 21(8); five experiments). Laughter comes from a
  violation that is also seen as benign: an alternative norm makes it acceptable, the violated norm
  matters little to them, or it is at a distance. Benign moral violations drew amusement as well as
  disgust. *For us:* a guess worth testing: the cheesy add-on jokes (J45) may fail because there is no
  violation at all (an ordinary thing personified), and a roast that lands is a violation kept benign
  by the warmth around it. Distance also matters for the crisis path: a joke about their own life with
  no distance is not benign.
- **Tangney et al. 1996** (J Pers Soc Psychol; 182 undergraduates described and rated their own
  embarrassment, shame and guilt). The three are distinct, not degrees of one feeling; shame was no more
  public than guilt, and many shame and guilt events happened alone. People judged themselves more
  harshly than they thought others did. *For us:* when they share something they are ashamed of, they
  are already their own harshest critic, so the reply should not add weight. For its own slips (J52),
  light embarrassment, not shame or guilt, is the tone that fits.
- **Varella Valentova et al. 2022** (Archives of Sexual Behavior 51(6); 1,744 people in Brazil, Chile
  and Portugal). Jealousy is defined as distress at a perceived threat to a valued relationship from a
  third party; the study itself is about how the sex of the person, partner and rival shapes it
  (same-sex rivals felt most threatening). *For us:* only the definition bears on idea 1: no rival, no
  valued bond under threat, no jealousy. The sex findings do not apply to a companion.
- **Oaten et al. 2018** (Frontiers in Behavioral Neuroscience 12; a pilot of 20 rating vignettes, an
  exploratory scan of 22). Moral "disgust" beyond the gross content itself looked like anger, and adding
  intent or responsibility raised both. *For us:* when they vent about what someone did to them, a
  reply on their side reads as anger scaled by how deliberate it was, not revulsion.

## Not for us

Needs like hunger and sleep for the companion, many-character relationship tables, and the full 54
channels.
