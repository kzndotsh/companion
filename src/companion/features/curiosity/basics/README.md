# Basics (J48)

It asks what to call them when memory does not know, then which pronouns they use when that is not set, and
keeps both answers. It exists because it once went about 700 messages without asking their name, and because how
they want to be referred to was only a setting the owner typed in, so a new user had no way to give it.

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

Asking their pronouns. Once the name is known, the same kind of note (`notes/ask-pronouns`) asks which pronouns
they use, in its own words and without making a thing of it. It is offered only when:

- how they want to be referred to is not set (the `address` setting, `core/turn/address.py`),
- a belief says what they are called (the name comes first),
- the turn is casual and no check-in note is offered,
- no ask-name has been logged in the last 24 hours, so the two never share a turn or a day,
- no ask-pronouns has been logged in the last 24 hours (decision key `basics: offered to ask their pronouns`).

Capturing their pronouns. After the turn is stored, if its last message asked about pronouns (a question mark
plus a pattern such as "pronoun", "she or he" or "refer to you") and the setting is still unset, one judge reads
that message and their answer (`system/pronoun-capture`, 3 s limit). The answer is kept only if it is at most 30
characters (`MAX_PRONOUN_CHARS`) and every word of it is in what they wrote, ignoring case and slashes. Code then
sets the `address` setting to it, so the pinned line (`notes/address`) carries it from the next turn. The
decision `basics: pronoun capture` is logged either way, with the prompt version. A failed or unreadable read sets
nothing and logs "no pronouns in their answer". A model never infers them: it only copies what they wrote.

The owner's setting is already set, so for the owner nothing changes: no pronoun note and no capture.
`companion address --set` still sets or replaces it by hand.

## Files

| File | What |
|---|---|
| `logic.py` | pure: when to ask the name or the pronouns, the notes, reading each from their answer, the belief a name becomes (`ASK_EVERY`, `MAX_NAME_WORDS`, `MAX_PRONOUN_CHARS`) |
| `run.py` | effects: the note (`basics_offer`), the captures once the turn is stored (`capture_name`, `capture_pronouns`, `judge_name`, `judge_pronouns`), the `Feature` (`BASICS`) |

## Prompts

- `notes/ask-name`: the line asking it to react first and then ask what to call them. System block.
- `system/name-capture`: gives the name they said they want to be called, or an empty string. Unreadable or empty means no name stored.
- `notes/ask-pronouns`: the line asking it to react first and then ask which pronouns they use. System block.
- `system/pronoun-capture`: gives the pronouns as they wrote them, or an empty string. Unreadable or empty means nothing set.

## Commands

- `uv run companion address`: how they want to be referred to, the setting the pronoun capture fills; `--set` sets it by hand.

## Measured

- 2026-10-19: code only, no talker measurement. A bare one-word answer the memory pass had missed was read and stored with their words as the quote (`evals/CHANGELOG.md`).
- Pronouns: not measured yet. Code and tests only.

## Tests

`tests/features/curiosity/basics/`
