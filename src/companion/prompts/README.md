# Prompts

Every prompt the bot sends lives here as versioned text, the persona included, and code loads it by
name (`from companion.prompts import get`).

## Rules

- A prompt is `name/vN.md`. `manifest.toml` says which version is current.
- Never edit a shipped version. Add the next `vN.md`, an entry in `CHANGELOG.md` and a line in
  `manifest.toml`. A test fails if any of those is missing.
- Placeholders are written `$name` and filled in with `render`. A missing value is an error.
- A decision a judge or extractor logs carries `name@version`, so a flag can be traced to the exact text.
- To try another version without shipping it: `COMPANION_PROMPT_OVERRIDES="system/ack=v2"` before the process starts.
- `uv run companion prompts` lists the current versions.

## How a request is assembled

There is no single overall system prompt. The talker's request has three parts, in this order:

1. **System block 1, the persona** (`system/persona`, about 1,800 words). It is the same on every turn,
   so the provider caches it.
2. **System block 2, the card**, rebuilt each turn: the clock line (`notes/clock`, `notes/clock-gap`),
   the memory lines (what is known about them, with how old each is, and the companion's own approved
   views), then any notes that apply this turn: the habit notes (`notes/habit-*`), the scene note
   (`notes/scene-*`), the length note (`notes/length`) and the listening note (`notes/listening-*`).
   Notes and memory ride here and never in a user message, because anything in a user message can be read
   as something they said.
   With `COMPANION_CHARACTER` set, block 1 is the persona, then `system/character-frame`, then the
   character sheet (`companion/characters.py`). The sheet wins on voice, taste, look and its own past;
   honesty, memory, closeness and limits still come from the persona.
3. **The messages**: the last 40 messages of the conversation, then their new message exactly as typed.

Everything else is a separate small model call with its own system prompt and a short excerpt of the
chat, and none of them sees the persona: the ack, frame, reaction, listening and habit judges, the
extractors for memory, the open-loop extractor and the follow-up draft, and the view checks. Each logs
`name@version` in its decision.

To see exactly what a past turn sent: `uv run companion replay <turn_id> --show-prompt`. How the
assembly has changed over time is in the `assembly` section of `CHANGELOG.md`.

## What is here

| Name | Kind | Used for | Current |
|---|---|---|---|
| `system/persona` | system | the talker's system prompt, the persona (its changelog entries carry the measurements) | v31 |
| `messages/spend-cap` | message | sent to the user once a day when the spend cap is hit | v1 |
| `notes/clock` | note | the clock line | v1 |
| `notes/clock-gap` | note | the gap since their last message | v1 |
| `notes/habit-echo` | note | their message has an emoji or emoticon the reply would copy, `core/habits.py` | v1 |
| `notes/habit-moves` | note | the habit finder found a habit | v1 |
| `notes/habit-opener` | note | an opening word is overused | v1 |
| `notes/habit-phrases` | note | phrases are repeated | v1 |
| `notes/length` | note | a short statement, `core/length.py` | v1 |
| `notes/length-serious` | note | a message judged serious, `core/length.py` | v1 |
| `notes/listening-everyday` | note | listening note, severity 1 | v3 |
| `notes/listening-health` | note | added to the severity 2 note for a health topic | v2 |
| `notes/listening-offer` | note | added to the severity 1 note when they were vague | v1 |
| `notes/listening-offer-serious` | note | added to the severity 2 note | v2 |
| `notes/listening-serious` | note | listening note, severity 2 | v5 |
| `notes/listening-trivial` | note | listening note, severity 0 | v2 |
| `notes/recall` | note | what the recall look-up found when they asked it to remember, `core/recall.py` | v1 |
| `notes/rude` | note | their message was rude to the companion, `core/listening.py` | v1 |
| `notes/scene-hypothetical` | note | they are exploring a what-if | v1 |
| `notes/scene-play` | note | a pretend scene is in progress | v1 |
| `notes/scene-story` | note | they are telling a story | v1 |
| `system/ack` | system | the ack judge, `core/ack.py` | v2 |
| `system/callback-judge` | system | the callback check, `core/callbacks.py`, `companion callbacks` | v2 |
| `system/character-frame` | system | the lines between the persona and a character sheet, `companion/characters.py` | v1 |
| `system/extract` | system | beliefs about the user, `core/beliefs/extract.py` | v8 |
| `system/frames` | system | the frame judge, `core/frames.py` | v1 |
| `system/habits` | system | the habit finder, `core/moves.py` | v2 |
| `system/judge` | system | the eval pass/fail judge, `evals/judge.py` | v1 |
| `system/judge-empathy` | system | the eval empathy judge, `evals/judge.py` | v1 |
| `system/listening` | system | the listening judge, `core/listening.py` | v3 |
| `system/openloops` | system | open-loop extraction, `core/openloops.py` | v3 |
| `system/openloops-draft` | system | the follow-up draft, `loops/openloops.py` | v2 |
| `system/react` | system | the reaction judge, `core/react.py` | v1 |
| `system/recall` | system | the recall look-up, `core/recall.py` | v1 |
| `system/self-extract` | system | the companion's own views, `core/beliefs/self_extract.py` | v4 |
| `system/views-conflict` | system | the view conflict check, `core/beliefs/views_conflict.py` | v1 |
| `system/views-implicated` | system | which views a flag implicates, `core/beliefs/views_implicated.py` | v1 |
