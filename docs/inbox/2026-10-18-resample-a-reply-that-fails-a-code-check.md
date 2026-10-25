# Resample a reply that fails a code check

**Status (2026-10-25):** built for replies: code checks redraw a reply once or twice (`docs/turn.md`, `COMPANION_RESAMPLE`, J47); a queue-time repeat filter for reach-outs is not built, card A9.

Added 2026-10-18. An idea, not a task.

## The idea

Before a reply is sent, plain code checks it for something we know is wrong. If the check fails, the
reply is thrown away and the same request goes to the model once more; the second answer is sent
whatever it is. One retry only, and the decision is logged with a reason written by code ("resampled:
the reply repeated their :3").

Nothing is edited: both replies are whole model outputs and code only chooses which one goes out, so
"never rewrite what the model said" still holds. It does shape what the user sees more than a note
does, which is why it is the last resort, behind changing what the model reads.

## Where it came from

The reply copied the user's emoji or emoticon (14 of 36 real messages with an emoticon, every time the
same one), and neither a note nor a persona change stopped it on ":3" (copied in 30 of 30 samples). The
everyday model on OpenRouter takes no logit bias, temperature or repetition penalty, so a resample is
the only hard lever left for it.

## What else a check could catch

Anything a deterministic check can spot with few false alarms:

- copying the user's symbol (the case above)
- restating their message: a long run of their own words in the reply
- formatting the persona forbids in plain chat: lists, headings, bold, asterisk actions outside a scene
- the system block leaking: the clock line, a bracketed note, "the user" or "the companion"
- a reply in another language than theirs (a flag reported a stray Russian reply)
- a reply far past the turn's length target (several times the words)
- the same opening word as the last few replies, or a question after a streak of questions
- an empty or cut-off reply

Phrases the owner has marked as unnatural could be a check too, but the owner has said a banned list
may be too limiting, so that one waits.

## What to weigh

- Precision first: a check that fires on good replies throws away good replies. Each check needs
  fixtures for both what it should and should not catch.
- A check only helps where the model fails sometimes, not always: when it copies every time, the retry
  copies too, and the fix is in what it reads (a note, the persona, the character sheet).
- Cost and time: one extra talker call (a fraction of a cent) and about a second on the turns where a
  check fires. Measure how often each check fires before turning it on.
- Never use it to handle risk or distress: that needs its own design, not a retry.
- Log every resample with the failed check, and keep the discarded reply in the decision detail so a
  replay can show both.
