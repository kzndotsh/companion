# Sending more than one message in a row, sometimes

**Status (2026-10-25):** partly built: replies are split into two or three messages at sentence boundaries (card S1, `COMPANION_SPLIT`, `io/split.py`, `docs/delivery.md`); afterthoughts and double texts on a timer are not built, card R11.

Added 2026-10-15. Nothing is decided. This is an idea to look at later, not a task.

## What was noticed

Every reply goes out as one block of text, with a pause while it is written. People who text do not
work like that. They send a thought, then a second one a moment later ("wait", "also", a reaction
to their own message, a correction), and sometimes they follow up after a gap with something they
only just thought of. Sometimes they send one short message and stop. The variety is part of why
texting feels like a person on the other end and not a form being filled in.

A companion that always sends exactly one message per message reads as a turn-taking machine, even
when each reply is good.

## The idea

Let a reply sometimes be two or three short messages instead of one, and let it sometimes send a
follow-up on its own a little later. Not a rule like "always split", because a pattern is as
mechanical as no pattern. The mix should come from the moment: a quick reaction then the real
answer, a thought and an afterthought, an excited burst, or just one line.

Possible shapes:

- **Burst.** One model reply holds several messages, sent a beat apart with typing shown between.
- **Afterthought.** One message now, and a second a few seconds to a few minutes later when the
  companion has something more to say. Needs a decision about whether it has one.
- **Double text after silence.** A follow-up when the user has gone quiet for a while and the
  companion would plausibly add something. Close to proactive messaging, which is its own question.

## Things to work out

- **How the model produces it.** The simplest way is a separator in the reply that the code splits
  on. That puts a formatting rule in the prompt and a parser in the loop. Another is a second,
  cheap call after the first message that decides whether there is a follow-up. That costs a call
  and adds a decision to log. A third is to let the talker call a "send message" tool several times.
- **What the ledger and history see.** Each message is an utterance in the ledger. Several in a row
  from the companion changes what the model sees next turn: its own pattern becomes part of the
  history and it will copy it, so a habit of splitting can harden into a tic. The same copying
  problem as repeated openers and phrases applies here.
- **Replay.** A turn is now one request and one reply and can be rebuilt exactly. A burst, and
  especially a delayed follow-up, needs every part recorded in order with its timing, or replay can
  no longer say what happened.
- **Interruptions.** The user may reply between the parts of a burst or before an afterthought
  arrives. The unsent parts then go stale and should probably be dropped, and what the user saw
  becomes the history.
- **Timing and cost.** Pauses between parts have to feel natural, not like a fixed delay. Typing
  indicators help. Every extra call costs money, and a delayed follow-up needs something running
  between turns.
- **Persona tension.** The persona asks for short replies and says a statement beats a question.
  Splitting could make a long reply into several short ones, which defeats the point. The
  rule has to be that each part is a real thought, not one sentence cut in half.
- **When not to split.** Someone who is upset, someone asking for an explanation, and a formal
  moment all want one clean message.
- **The reactions already in use.** Quick acknowledgements are sent as an emoji reaction. A burst
  that begins with a one-word reaction may overlap with that.

## How it could be tested

- A fixture where a good reply is naturally two beats (a reaction, then the substance), with a
  judge asking whether the parts are separate thoughts and whether one message would have read
  worse.
- A fixture where it should stay as one message.
- Over a whole replayed conversation, measure how often it splits and whether the pattern repeats
  turn after turn, the same way the repeated-opener check does.
- A check that the user sees the same history the model does after an interruption.

## Questions for later

- Should splitting be decided by the model, by the moment (code), or by something like a cheap
  judge, as with the ack and frame judges?
- Is a delayed follow-up worth it before there is any proactive messaging at all?
- What is the smallest version worth trying first? Probably a burst of two parts on a clear
  trigger, behind a flag, with every part logged.
