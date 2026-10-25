# Tools the companion could use

**Status (2026-10-25):** partly built the code-decides way: recall look-up and reminders (`src/companion/features/reminders/`); web search and true tool calls are not built, no card.

Added 2026-10-18. To brainstorm; nothing decided.

## How tools usually work

In a coding harness, the model's request carries a list of tools (a name, a description, an input
schema). Instead of only writing text, the model can answer "call read_file with this path"; the
harness runs it, sends the result back, and the model continues, calling more tools or writing its
answer. The model decides when it needs something.

## How this project does it today

Code decides, the model talks. Everything the companion knows for a turn is put in front of it before it
writes: the memory card, the clock, the notes. The recall look-up of 2026-10-18 is a tool done this way:
the listening judge notices "you know this one", code searches all beliefs, and the finds ride that
turn's system block. The talker never calls anything itself, which keeps every turn replayable, logged
with a reason written by code (ADR 0006, 0014), fast and cheap.

## Candidates

- Web search: weather, whether a film is out, a score, the news. The persona says today that it cannot
  look things up.
- A deeper memory search mid-reply, beyond what the recall look-up hands it.
- Actions: set a reminder, save a note, send a picture, start music.
- Knowing what time it is somewhere else, or doing arithmetic it would otherwise guess.

## Two ways to do each

1. Our way: a judge labels the need ("they asked about something current"), code runs it, the result
   rides the card. Replayable and cheap, nothing new for the model to misuse; only works for needs that
   can be spotted from the message.
2. True tool calls: the talker gets the tool list and calls what it wants. Handles needs code cannot
   anticipate, but adds a round trip (a second or more) per call, the model can call wrongly or too often,
   and replay must record each call and its result.

## Things to settle

- Which needs can be spotted cheaply enough for way 1, and which truly need way 2.
- What the companion says when it used a tool ("I looked it up" breaks the friend register?).
- Safety rules from the audits (A37): an allowlist, no delete tool, idempotency keys on any action, the
  recipient by id, results framed as data, never instructions.
- Cost and latency per turn, measured before anything ships.
