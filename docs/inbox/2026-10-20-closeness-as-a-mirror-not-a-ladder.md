# Closeness as a mirror of what they have shown, not a ladder

**Status (2026-10-25):** not built; waits on the owner's say with T2, card T17.

Added 2026-10-20. An idea, not a task. It reshapes T17 (closeness stage) and could answer T2 (pacing).

## The original idea

A closeness stage computed in code from real history (how long they have talked, how much they have
shared, how often they flirt) picks one note line from "just met" up to "close", so intimacy is paced by
how well the two know each other. It steps down only slowly, after a long quiet, and never guilts.

## Why a ladder is the wrong shape

- **Relationships with chatbots do not follow fixed stages.** Interviews with companion-app users over 12
  weeks (Skjuve et al. 2021, 2022) found closeness deepens through sharing, but with large variation in
  when sharing starts; the authors doubt human stage models fit. Some users lead fast from the first day.
- **A ladder that starts at "just met" makes the bot colder** with anyone who has already led further,
  and a character sheet may already set the starting warmth.
- **Visible levels that unlock intimacy are flagged as a dark pattern** in a 2026 audit of the top five
  EU and UK companion apps (contested among the annotators). Anything that rewards coming back, or guilts
  leaving, raises churn intent once noticed (De Freitas et al.).
- **A stage note is a prompt rule.** Structural fixes beat prompt rules here as elsewhere.

What does help, measured: relational behaviour over time (small talk, empathy, memory, humour) raised
trust and the wish to continue in a month-long study (Bickmore and Picard 2005); varied wording helped
long-term use; a bot sharing about itself drew deeper sharing back (CHI 2020), which makes its own
disclosure a lever to cap, not to push.

## The idea instead: a mirror that sets ceilings

Code keeps, per dimension, how far the user has gone:

- **Depth shared:** the deepest level of memory they have given (the memory map's surface, personal,
  core labels).
- **Affection:** whether they started affection, flirting or a romantic frame (listening labels, scenes
  they began).
- **Names:** which names and pet names they have used or accepted, and which they asked it to stop using.

Nothing is said to the talker. The mirror only sets ceilings on features that already exist:

- the questions it asks to get to know them (J48) never go deeper than they have shared;
- how often it shares its own tastes and stories (ADR 0020) stays capped until they share at that depth;
- pet names come only from the accepted list (J12, phase 2);
- how often it may reach out (initiative).

It only rises through what the user does, so it follows their lead and cannot be farmed.

## Pieces that could sit beside it

- **A user setting** ("quick", "natural", "slow burn"), the dial T2 asks about, to override the mirror.
- **After a long quiet** (say two weeks), the first replies come back gently warm rather than picking up
  mid-flirt, never mention the absence, and let them restart. Nothing measured says how; fixtures would.

## Not doing

A visible meter or level, unlocks, the stage named in any reply, rewards for returning, guilt for leaving.

## How it could be tested

- Work the mirror out in shadow over past history, day by day, and read it by eye.
- Its first use: gate J48's question depth, which already runs in shadow, and compare the picks.
- Fixtures for a user who leads fast and one who leads slowly, checking the bot follows each.
