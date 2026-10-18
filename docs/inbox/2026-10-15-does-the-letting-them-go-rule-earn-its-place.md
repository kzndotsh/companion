# Does the "letting them go" persona rule earn its place?

Added 2026-10-15. Nothing is decided. This is parked until there is something to test it with.

## The rule

The live persona (`src/companion/prompts/system/persona/v11.md`, which keeps this section from v10) has a short section called "Letting them go":

> When they say they are going to eat, sleep, work or leave, let them go. A short send-off is
> enough, or nothing. Do not ask whether they have done something they have only just said they
> are about to do, and do not act as if time has passed: it has not passed until the clock line
> says it has.

The previous version (`v9.md`) is identical except that it lacks this section. v10 adds about 70
tokens and nothing else.

## Where it came from

The first persona draft had one sentence like it ("if someone says they are going to sleep, work,
or leave, let them go"). It was lost in a later rewrite and nobody noticed for eight versions. The
rule was restored, and expanded, after a flagged turn: the user said they were about to go and do
something, agreed to go, and the companion replied as if they had already left and come back
("did you actually eat or are you lying to me").

## What was measured

The eval runner (`uv run companion eval`, see `evals/README.md`) replayed that turn against both
versions. Over two runs, 7 samples per version:

- the flagged turn (fixture `signoff-then-time-skip`): v9 0/7, v10 0/7. The rule changed nothing.
  The replies are nearly identical. The previous message set up a running joke, and the model keeps
  the joke going whatever the persona says.
- a plain goodbye with no joke running (fixture `control-short-send-off`): both versions already
  pass, so there is no failure for the rule to fix.
- a side check on a different fixture (`play-invitation`): v9 5/7, v10 2/7. Suggestive but not
  significant (about a 12% chance of luck), and no known reason the rule would cause it.

## Why it is inconclusive

The case the rule was written for (a plain goodbye) already works, and the case that failed (a
goodbye inside a running joke) is not fixed by a prompt rule. So there is currently no example
where the rule helps, and so nothing to measure it against. In the live loop the flagged case is
handled separately: a short acknowledgement gets an emoji reaction instead of a reply
(`src/companion/core/ack.py`).

## Options

**A. Keep it.** Cheap, easy to revert, and it matches the original intent. Risk: an unproven rule,
and the weak hint that it may nudge play handling the wrong way.

**B. Revert to v9.** Simpler and shorter, with no rule we cannot show working. If a plain goodbye
goes wrong later, add it back, and this time with a fixture.

**C. Settle the side question.** About 12 samples per version on the play fixture would show
whether v10 really does worse there. Roughly 10 cents.

## When to look at this again

- A goodbye goes wrong in real use outside a running joke, and gets flagged. That is a failing
  case, so the rule can be tested properly.
- The play stance gets worked on. That is a natural moment to run the play comparison.
- Otherwise, if it is still here in a month with no new evidence, pick A or B and delete this.

## Related

- `src/companion/prompts/CHANGELOG.md`, entries for v10 and the v9 versus v10 measurement.
