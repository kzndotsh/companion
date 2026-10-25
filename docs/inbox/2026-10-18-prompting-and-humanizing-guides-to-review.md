# Prompting and humanizing guides to review

**Status (2026-10-25):** reviewed 2026-10-18 (`docs/research/2026-10-18_prompting-guides-review.md`); no card for acting on it.

Added 2026-10-18. **Reviewed the same day:** see `docs/research/2026-10-18_prompting-guides-review.md` for
what each says, what lines up with our measurements and six candidate experiments. The original list
is kept below.

## The links

- https://www.actmorehuman.com/guides/humanize-llm-prompts (probably prompt techniques for
  human-sounding output)
- https://www.actmorehuman.com/hi/guides/how-to-make-claude-sound-more-human (probably the
  Claude-specific version of the same guide)
- https://github.com/hexiecs/talk-normal/ (a repository, possibly a prompt or a rule set for
  talking less like a model)
- https://github.com/blader/humanizer (a repository, possibly a catalogue of machine-writing tells
  and how to remove them)
- https://claude.com/blog/best-practices-for-prompt-engineering (Anthropic's prompting advice)
- https://developers.openai.com/api/docs/guides/prompt-guidance (OpenAI's prompting advice)

## Why they might help

The owner's flags keep landing on the same few habits: restating a detail instead of adding
something, cheesy quips, replies that interrogate, and empathy that is a template. Several fixes by
prompt text alone have failed here (a persona line against restating moved the judged score from
0 of 12 to 3 of 12), and the ones that worked were short per-turn notes in the system block. These
guides may name more tells, show wording that holds up better, or say where in a prompt an
instruction is read most reliably.

## What to look for when reading

- Concrete techniques that could be tried as a persona change or a per-turn note, with the reason
  given for why they work.
- Lists of machine tells (openers, hedges, "not X, it's Y", forced warmth, stock sympathy) that could
  become fixtures or deterministic checks.
- Where instructions go in a prompt, how long they can be, and whether positive wording ("do X")
  beats negative wording ("don't do Y") for this kind of output.
- Anything that contradicts what has been measured here. Treat a claim as a hypothesis until it is
  run on the fixtures at 12 to 30 samples.

## How to use what is found

Write each candidate technique as a persona version or a `+flag` variant, run it against the public
fixtures and the real flagged turns with a stated spend cap, read the replies by eye as well as
with a judge, and record the numbers in `evals/CHANGELOG.md`. Nothing from a guide goes live on the
strength of the guide.

## Related

The restating habit (T10, parked) and the substance question for trivial vents (T14) in
`TODO.md`, and `docs/inbox/2026-10-17-restating-the-users-point-research-and-measurement.md`.
