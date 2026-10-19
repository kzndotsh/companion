# XML tags for the system block

Added 2026-10-19. An idea, not a task.

## The idea

The talker's second system block holds the clock line, the memory card and this turn's notes as plain
text with headings ("What you remember about them", "Also known, but only touch it if they bring it
up") and bracketed note lines. Wrapping each part in a tag, such as `<clock>`, `<memory>`, `<held>` and
`<notes>`, might draw a sharper line between what the companion knows and what it should do this turn.

Prompting guides still recommend tags for separating material from instructions in long prompts
(Anthropic's guide for Claude, OpenAI's GPT-4.1 guide for documents). How much that holds for current
models is a guess, not checked.

## Why not now

- Nothing shows it is needed: no flag so far shows the model mixing up a memory with an instruction.
- The known risk is the opposite: a chat model that sees markup can echo it. A bracketed clock line was
  copied into replies before (persona v17 in `src/companion/prompts/CHANGELOG.md`), and tags could leak
  the same way.
- Short single-line notes gain nothing from tags; the brackets already mark them as asides (a test in
  `tests/test_prompts.py` keeps every note bracketed, apart from the clock and the listening parts).

## How it would be measured

Run the public fixtures, the memory and recall fixtures and a leak check (a `not_regex` for `<` and the
tag names) with the current format and the tagged one, 12 samples or more per cell, on the live talker
and one other model. It ships only if it fixes something real with no rise in leaks.

## What would make it a task

A flag where the reply treats a memory as an instruction, recites the card, or follows a note as if the
user said it.
