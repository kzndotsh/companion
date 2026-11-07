# Reactions

Reactions are the turn's own stage, not a feature: the listen stage runs the instead judge, the talk stage starts the alongside one beside the talker and the persist stage applies it (`turn/reactions.py`), so no feature declares them. Their pure rules are in `core/turn/reactions.py`.

An emoji on their message, sent in place of a reply or beside one, so it answers the way a friend does: a heart for a sweet line, a thumbs up for an "ok". Two small judges decide it, and code applies a rule to what they score.

**Status:** live. No switch of its own; it needs the judge model (`COMPANION_JUDGE_ROUTES` can route either judge by its name, `ack` or `reaction`). The crisis path (`COMPANION_CRISIS`) turns the first one off for a message with a cue word.

## How it works

**The instead judge** decides a reaction in place of a reply. A code prefilter asks the model only when the message is short (40 characters, 4 words), has no question mark and no stretched word ("fineee"), the companion's last message did not ask anything, and their message before this one was not judged serious (a bare "thanks" after something heavy deserves words). A message with a crisis cue word never reaches it (ADR 0022). The model reads the last 8 messages and returns a kind and a confidence. Code reacts only on `ack` at 0.70 or more (`INSTEAD_THRESHOLD`); anything else gets a reply. A failed or late read (2 s) means a reply.

**The alongside judge** decides a reaction as well as a reply. It runs beside the talker, so it adds no wait. The model returns a tone (funny, sweet, impressive, exciting, sad or plain), a confidence and an emoji. Code reacts only when the tone is not plain or sad, the confidence is 0.65 or more, and at least 3 of their messages have passed since the last reaction (`MIN_GAP`), so a reaction stays occasional. A failed or late read (2.5 s) means no reaction. The tone it reads also feeds the mood (`mood`).

Both write a decision with the scores, the model, the prompt and its inputs hash. The reason is built by code from the scores, never by the model (ADR 0006). A reaction is never an edit of a reply. The names logged and routed by stay as they were: the decision keys (`ack: replied`, `react: none`, and `REACTED`), the judge names `ack` and `reaction`, and the prompt files.

## Files

| File | What |
|---|---|
| `core/turn/reactions.py` | pure: both judges' schemas and reads (`InsteadRead`, `ToneRead`), the prefilter (`is_candidate`), the thresholds, `reaction_instead`, `reaction_alongside` and the reasons |
| `turn/reactions.py` | effects: the two `Judge` declarations, `react_instead` (the listen stage runs it), `react_alongside` (the persist stage runs it) and the logged decisions |

The reaction types a turn hands to the chat (`Reaction`, `ReactAndReply`, `ThenSend`) are in `core/turn/reply.py`, because delivery sends them. What a small judge reads of the chat (`conversation_prompt`, one shape for every judge that reads a transcript), the hashes a logged decision keeps, and `Scored` (a read with its model and prompt, which builds the standard decision detail) are in `core/turn/context.py`. `stretched` is in `core/turn/energy.py`, which `marks` also uses.

## Prompts

- `system/ack`: the instead judge's prompt: whether a short message only acknowledges.
- `system/react`: the alongside judge's prompt: the tone of a message and an emoji that fits it.

## Commands

None. Read the decisions in the decision log (`companion replay <turn_id>`).

## Measured

- 2026-11-02: the instead judge needs 8 messages of context, more does not change it (`evals/CHANGELOG.md`).
- 2026-11-05: a message with a stretched word never goes to the instead judge (`evals/CHANGELOG.md`).

## Tests

`tests/core/turn/test_reactions_*.py`, `tests/turn/test_reactions_*_loop.py`
