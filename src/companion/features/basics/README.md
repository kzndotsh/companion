# Basics (J48)

It asks what to call them when memory does not know, and remembers the answer. It exists because it once went
about 700 messages without asking their name.

**Status:** live. No switch. It runs as a note before the reply and as a step after the turn is stored.

## How it works

Asking. On a casual turn (read as not serious, not in a scene, not a goodbye) a note goes into the system block
that says it does not know what they like to be called and asks it to react first, then ask once and lightly.
Code decides, not a model. The note is offered only when:

- no current belief about them says what they are called (`knows_name`, a pattern over the claim text),
- no check-in note is offered this turn,
- no ask-name has been logged in the last 24 hours (`ASK_EVERY`, decision key `basics: offered to ask what to call them`).

The log line is written only once the turn is stored, so a turn that fails does not use up the day.

Capturing. After the turn is stored, if its last message asked what to call them (a question mark plus a
pattern such as "your name" or "call you") and memory still has no name, one judge reads that message and their
answer (`system/name-capture`, 3 s limit). The name is kept only if it is at most 3 words and appears in what
they wrote, ignoring case. It is stored as a trait belief, stated, confidence 0.9, quoting their own answer, in
their frame (ADR 0001). The decision `basics: name capture` is logged either way, with the prompt version. A
failed or unreadable read stores no name and logs "no name in their answer".

Not here: how they want to be referred to is a separate setting (`companion address`, `core/turn/address.py`),
pinned after the clock on every turn.

## Files

| File | What |
|---|---|
| `logic.py` | pure: when to ask, the note, reading a name from their answer, the belief it becomes (`ASK_EVERY`, `MAX_NAME_WORDS`) |
| `run.py` | effects: the note (`name_offer`), the capture once the turn is stored (`capture_name`, `judge_name`), the `Feature` (`BASICS`) |

## Prompts

- `notes/ask-name`: the line asking it to react first and then ask what to call them. System block.
- `system/name-capture`: gives the name they said they want to be called, or an empty string. Unreadable or empty means no name stored.

## Commands

- `uv run companion address`: how they want to be referred to (a separate setting, not this feature).

## Measured

- 2026-10-19: code only, no talker measurement. A bare one-word answer the memory pass had missed was read and stored with their words as the quote (`evals/CHANGELOG.md`).

## Tests

`tests/features/basics/`
