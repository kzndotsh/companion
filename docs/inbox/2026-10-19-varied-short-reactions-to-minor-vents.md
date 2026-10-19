# Varied short reactions to minor vents

Added 2026-10-19. An idea, not a task.

## The problem

When someone vents about something minor, the model restates their situation back as its sympathy
("that's so annoying when you're ready to crash and the bed's still waiting on laundry"). On a real flagged
turn it did this 30 of 30 times with the shipped note, with a note that named and banned the clause, with a
six-word cap, with a short history window, and on a second model family. Two tiny examples of the right size
in the note (`notes/listening-trivial` v5) cut it to 24 of 30 but made replies converge on one line ("ugh,
that's so frustrating 😭" 23 of 30 on another fixture). v5 shipped anyway because short and plain is
acceptable; the retelling and the sameness are still open. Measurements in `evals/CHANGELOG.md`.

## What research says (2026-10-19, summaries only)

- One empathy template covers 83 to 90% of LLM replies to venting, and people rate it as more empathic
  than the more varied human replies (preprint, arXiv 2604.08479). Human supporters restate in about 7% of
  turns (ESConv). The habit is trained and well liked, which is why prompts do not move it.
- Few-shot examples bias output toward copying them, especially the most recent one (arXiv 2102.09690),
  which matches the collapse onto one line.
- Asking a model for several responses with how likely each is (verbalized sampling, arXiv 2510.01171)
  raised diversity 1.6 to 2.1 times in creative writing; not measured on chat.

## Ideas, in the order to try

1. **A rotating pool of examples.** 30 to 50 short, varied, generic reactions (a bare "noooo", "ugh i hate
   that", "same tbh", a small wish, a quick "this happened to me too"), with code drawing two or three
   different ones per turn, seeded by the turn id so a replay matches. Measure the retelling rate and the
   number of distinct replies across 30 samples against v5.
2. **Several candidates in one call, code picks.** The model writes five short options; code picks the one
   sharing the fewest content words with their message, avoiding the most typical one. One larger call.
3. **Plain best-of-n** is ruled out for now: a single clean sample was 0 of 30 before v5. Worth rechecking
   on v5, where about 1 in 5 is clean.

## What would make it a task

A flag on a reply that retells a minor vent again, or on minor-vent replies all sounding the same.
