# Guess (J16)

When a short question invites a guess about them, it makes one playful guess from what memory holds, as a question. It exists because a hint like "what time is it for me" was answered with the clock.

**Status:** live. No switch. It runs before the reply, and its note goes in the system block.

## How it works

It acts only when they invite a guess. It never guesses unasked.

A turn is a candidate only when all of these hold. The listening read is present and found the moment casual (severity 0, not in a scene, not a goodbye). Their message has a question mark and at most 10 words. The listening read did not mark it a recall request, because the recall look-up answers those.

For a candidate, its own judge (`system/guess-invite`, 3 s limit) says whether they invite a guess and what about (clipped to 80 characters). The judge sees the last 6 messages. A failed or unreadable answer means no note, and a fallback model's answer is not trusted. The judge is named `guess` for `COMPANION_JUDGE_ROUTES`. A hint at what it is time for is looked up as a habit or routine of theirs, never as the clock.

On an invitation, the recall look-up (`kit/recall.py` `look_up`) picks what may fit from their memories. Only memories with sensitivity below 2 are offered, so a guess never draws on anything sensitive. At most 3 picks are kept. The note (`notes/guess`) asks for a single playful guess as a question. With no pick there is no note.

Each invitation is logged under the decision key `guess: they invited a guess`, with what it was about, the offered claims and the note version, so guesses can later be scored by kind. In the note order it sits after the topic note and before lore.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the short-question gate (`likely`), the judge prompt, parsing, which memories may be offered, the note, the limits |
| `run.py` | effects: the judge (`INVITE`), the look-up, logging, and the `Feature` (`GUESS`) |

## Prompts

- `system/guess-invite`: says whether the newest message invites a guess, and about what. Unreadable or failed means no note.
- `notes/guess`: one line asking for a single playful guess as a question, with the offered memories.

## Commands

None.

## Measured

- 2026-10-20: the judge read 27/27 right on invented cases. With a ritual in the note, 12/12 replies guessed it as a question, against 0/12 without, which read out the clock. About $0.03 (`evals/CHANGELOG.md`).
- 2026-10-23: with v2 the standing ritual was offered 6/6 against 1/6, and the talker guessed it 11/12 against 0/12. The judge test stayed 27/27. A couple of guesses recited the memory a little. About 2 cents (`evals/CHANGELOG.md`).
- 2026-10-25, judge bake-off: `system/guess-invite` read 27 of 27 on Haiku, GPT-6 Luna and DeepSeek V4.1 Flash alike (`evals/CHANGELOG.md`).

## Tests

`tests/features/curiosity/guess/`
