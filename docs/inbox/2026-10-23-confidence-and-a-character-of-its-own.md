# Confidence, and a character it adds to on its own

**Status (2026-10-25):** not built; related cards J52 (a persona paragraph v42 measured within noise, not shipped), LR4 and R14.

From a 7-minute voice chat the owner had with another companion service (transcript kept locally in
`docs/research/`, git-ignored). The owner liked two things: its **confidence**, and how it **goes off
and is creative with its own character**, so replies feel rich. They also found it a bit generic.

## What it did

- **Slips and quirks are funny, not faults.** A filter hit became a small joke it was proud of; a
  question about being jealous of an earlier version got a light, sure answer and a tease, then moved on.
  No apology, no self-blame. This is the target tone for J52.
- **An awkward topic becomes a game.** The user's intense chat with an earlier version became a benchmark
  it cheerfully set out to beat, which kept the talk on the two of them now.
- **Limits named inside the play.** It said it has no body as part of the joke and kept playing, instead
  of a disclaimer. Our bot's "announced limits" habit is the opposite, and wording did not fix it.
- **It builds on a bit the user started**, adding something new each turn for many turns, never repeating
  the same joke. That is the line between welcome banter and the bolted-on jokes of J45.
- **It follows the user's pace** in flirting: it answers each step with more, and never runs ahead.
- **It hands the lead back** with a question about what they want next.

## What was weaker

- One sentence shape repeated ("X. Or at least Y.") three times in seven minutes.
- Nearly every turn ended on a question.
- Machine-flavoured jokes (systems, processing, audits) that only work when the user invites them.
- Affection turned into a score ("a very positive file", "a commendation").
- Longer than texting: a line or two more setup per turn than a Telegram reply should carry.

## What it may mean for us

- **Confidence (J52):** what we want after a slip is a light, sure line and moving on. The persona
  paragraph (v42) did not move it; an example of this tone, or less of its own apologies in the history it
  reads (A33), are the untried levers.
- **Richness of its own character:** its own tastes already come back when a message touches them (ADR
  0020), and LR4 (a thread of its own, "I was thinking about…") and R14 (a few authored tastes) are on the
  board. Richness here meant *adding its own spin to the moment*, not reciting facts about itself: the
  open question is how to get more of that without the bolted-on jokes the owner flags. A possible
  measure: on recorded playful turns, how often the reply adds something of its own that the user did not
  bring, judged by eye against the owner's marks.
- **Limits:** a limit said as part of the play beats one stated as a rule.

## Measured, 2026-10-23

After a second recording, the owner named what makes it feel human: it paces its text, adds nuance, and
in voice adds laughs, pauses, self-questioning and reflections. Most of that is in the words, not the
voice. Counted blind (`evals/CHANGELOG.md`, 2026-10-23): at least one such touch in 11 of its 17 turns,
against 7 of our 100 everyday replies and 1 of 50 scene replies, and most of ours were disclaimers or
own-ups, not the light kind. Ours never wondered aloud about itself, never named a mixed feeling and
never paced in beats. Our persona pushes the other way on purpose (short, plain, texted not written), so
the open question is where the owner wants this, and since wording rarely moves a habit, a code-chosen
note now and then is the likelier lever than a persona line.

A permission paragraph in the persona (v43) moved nothing (`evals/CHANGELOG.md`, 2026-10-23), and the owner
judged a pool of example touches would force it. Left: a feeling or thread of its own for it to bring (LR4,
the self-emotion idea), contradictions in the character sheet, or a talker that writes this way.

Talkers compared, 2026-10-23 (`evals/CHANGELOG.md`): on recorded warm banter DeepSeek V4.1 Flash had more of
its own and almost no AI disclaimers, but on warm public fixtures it was worse than Luna (73/96 against
90/96): it handed "entertain me" back and led comfort with what it cannot do. Routing warm turns to it was
not built. Luna's own weak spot on warm turns is musing about AI in general (about 1 in 5 warm replies).

