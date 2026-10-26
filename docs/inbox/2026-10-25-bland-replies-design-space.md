# Bland replies that hand their message back: the whole design space

Not a task yet. A brainstorm from 2026-10-25 after a flag ("basic reply that i see often") and a day of
measurement. Every number below is in `evals/CHANGELOG.md` under that date.

## The problem, as measured

In casual chat many replies only agree with or restate what they said, often with a flourish or a
stock frame, and add nothing: "that sounds like a really good lunch, especially the potatoes, how did
you cook it?". Two Claude raters called 21 to 47% of 226 recent casual replies echoes. Replies that
land do something else: a take of its own with a reason, a bit that builds on theirs, a callback, a
guess, a question that goes somewhere new.

## What causes it (what the tests ruled in and out)

- **Not the model, mostly.** Fourteen talkers on the same 12 echo turns: the best (GLM-5.3, MiniMax M3.1
  Flash) added something in about 40% of replies, Luna in about 25%. Every model, given our prompt,
  lands in the same place.
- **Not thinking time.** Luna at high reasoning: no change. Luna Pro: no change, 13 times the cost.
- **Partly the prompt load.** No single note does it, but the 3 to 9 note lines each turn plus the
  persona rule that an ordinary thing gets "a plain reaction or a plain question, no joke" cost about a
  third of the replies that would add something (22 to 32 of 72 when removed). A stripped persona did
  not help and lost rules that do real work (it lectured about its limits).
- **Mostly a trained default.** With everything removed, still under half the replies add something.
  Research: chat models are trained toward affirming narration and agreeing with the user, and
  prompt-level fixes give mixed results (ELEPHANT, ICLR 2026; affirmative narration, 2026).
- **The model can do it when asked.** One note asking for one thing of its own took adds to 61 to 62 of
  72. Its costs: its own words became a new template ("I'd pick the potatoes" four times), and it
  pushed opinions into a turn where they were comforting the companion.

## What good looks like

A friend who brings themselves, not one who adds something every time. Some replies should just
react ("lmao no"). Never at a tender moment (they are comforting it, being affectionate, hurting).
Never cheesy (the quips that the "plain" rule was written against). No new template. No longer replies
for the sake of it. The rate of echoes should fall from about a third to well under a fifth, measured.

## The design space

### A. Subtract first (the prompt)

1. **Rewrite the ordinary-things rule as something to do.** Keep what it was for (no personifying the
   laundry, no "side quest" framing) and drop "plain reaction or plain question". Measured on the echo
   turns and the old cheesy-quip fixtures together, so the quips do not come back.
2. **Remove what code already enforces.** The reply checks redraw an em dash, markdown, an unasked AI
   disclaimer, a copied clock line, the stock "especially when" line and "a beat". The persona still
   spends words asking for the same things. Each duplicate is weight with no effect.
3. **A note budget.** Standing facts (their pronouns) belong on the card as facts, not as a fresh
   instruction every turn. At most one mood line. A habit warning only when the habit is strong. A cap
   on note lines per turn, kept in a fixed priority order, so new notes cannot pile up unseen.
4. **Turn "don'ts" into who it is.** v41 has 51 "do not / never" lines. Where a rule is about character
   ("you have your own taste"), say it as character; where it is about form, enforce it in code.

### B. Add a contribution

5. **A move picker (plan, then write).** Code picks one kind of move for the turn (its own take, a
   detail they may not know, build on their bit, a callback, a new angle) and a line after the history
   describes it in words with nothing to copy; moves rotate so no template forms. Dialogue research
   supports planning the act before writing the words.
6. **Gate by kind of message.** The listening judge adds one label: a share, a joke or riff, a
   question, tender (affection, comfort, toward the companion), a vent, logistics or a goodbye. Tender
   gets no move; a vent keeps the listening notes; a joke gets "build on it". Today these turns all read
   "severity 0, other".
7. **Feed the move real material.** Prefer something it has: one of its own tastes (lore), a memory
   near the topic (relevance), something from earlier in the chat (episodes). Code chooses the material;
   the move is only "say what you think" when nothing fits. A move with nothing behind it invents filler.
8. **Best of several.** Draw two or three replies and let a small judge pick the one that adds the most
   without being forced. No prompt change, no template, the model's own variety does the work; at a 25%
   base rate, three draws give a reply that adds something about 58% of the time if the judge picks
   well. Cost about three times a reply (still pennies) and a judge call; a second or two slower, which
   the owner accepts. Risk: judges were loose today (a check flagged a quarter of good replies), but
   ranking is easier than flagging.
9. **Only when needed.** Whatever adds, it fires after the last reply or two echoed, not every turn, so
   the rhythm stays human.

### C. Measure all the time

10. **An echo meter.** After each casual reply, a small judge labels it adds, echo or other, beside the
    turn like the habit check. The rate per day is a number to watch and the trigger for 9.
11. **Cheaper marks from the owner.** A reaction emoji on a reply in Telegram or Discord (a thumbs up, a yawn) as a
    one-tap label, much easier than `/fav` (rarely used). Every mark is data for tuning and for later.

### D. Longer term

12. **Tune a talker on its own logs.** Research says this habit is set in training. The meter's labels,
    the marks and the flagged turns are the data a preference-tuned talker would need. Months away;
    collect now.
13. **Revisit the talker only for overall quality.** Sonnet 5.5 had the most natural voice but
    disclaimed being an AI three times; GLM-5.3 and MiniMax add a little more. Not a fix for blandness.

## What to build first, and how to know

Subtract, then compare two ways of adding, then keep the winner behind a meter.

1. A1 to A3, each measured alone and together on the 12 echo turns, a set of tender turns and the
   cheesy-quip fixtures: adds, echo, forced, cheesy, by two blind Claude judges.
2. A bake-off on the lighter prompt: the move picker with the message-kind gate (5 to 7) against best of
   several (8), same turns, same judges, plus a template count (the most repeated opening words across
   replies). Pick by adds without forced, cheesy or tender misses.
3. The echo meter (10) ships first, in shadow, so the before and after are real-chat numbers.
4. The winner goes live gated by 9, behind its switch, with a review date.

## Open questions for the owner

- How much adding is right? A friend does not contribute every message. A target (say four replies in
  five that are not echoes) would set the trigger.
- Reactions (Telegram or Discord) as marks: wanted?
