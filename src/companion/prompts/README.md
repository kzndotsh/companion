# Prompts

Every prompt the bot sends besides the persona lives here as versioned text, and code loads it by
name (`from companion.prompts import get`). The persona keeps its own folder and the same rules:
`src/companion/persona/` (`vN.md`, `CHANGELOG.md`, `ASSEMBLY.md`).

## Rules

- A prompt is `name/vN.md`. `manifest.toml` says which version is current.
- Never edit a shipped version. Add the next `vN.md`, an entry in `CHANGELOG.md` and a line in
  `manifest.toml`. A test fails if any of those is missing.
- Placeholders are written `$name` and filled in with `render`. A missing value is an error.
- A decision a judge or extractor logs carries `name@version`, so a flag can be traced to the exact text.
- To try another version without shipping it: `COMPANION_PROMPT_OVERRIDES="ack=v2"` before the process starts.
- `uv run companion prompts` lists the current versions.

## What is here

| Name | Kind | Used for | Current |
|---|---|---|---|
| `messages/spend-cap` | message | sent to the user once a day when the spend cap is hit | v1 |
| `notes/clock` | note | the clock line | v1 |
| `notes/clock-gap` | note | the gap since their last message | v1 |
| `notes/habit-moves` | note | the habit finder found a habit | v1 |
| `notes/habit-opener` | note | an opening word is overused | v1 |
| `notes/habit-phrases` | note | phrases are repeated | v1 |
| `notes/length` | note | a short statement, `core/length.py` | v1 |
| `notes/listening-everyday` | note | listening note, severity 1 | v2 |
| `notes/listening-health` | note | added to the severity 2 note for a health topic | v2 |
| `notes/listening-offer` | note | added to the severity 1 note when they were vague | v1 |
| `notes/listening-offer-serious` | note | added to the severity 2 note | v2 |
| `notes/listening-serious` | note | listening note, severity 2 | v3 |
| `notes/listening-trivial` | note | listening note, severity 0 | v2 |
| `notes/scene-hypothetical` | note | they are exploring a what-if | v1 |
| `notes/scene-play` | note | a pretend scene is in progress | v1 |
| `notes/scene-story` | note | they are telling a story | v1 |
| `system/ack` | system | the ack judge, `core/ack.py` | v2 |
| `system/extract` | system | beliefs about the user, `core/beliefs/extract.py` | v8 |
| `system/frames` | system | the frame judge, `core/frames.py` | v1 |
| `system/habits` | system | the habit finder, `core/moves.py` | v2 |
| `system/judge` | system | the eval pass/fail judge, `evals/judge.py` | v1 |
| `system/judge-empathy` | system | the eval empathy judge, `evals/judge.py` | v1 |
| `system/listening` | system | the listening judge, `core/listening.py` | v1 |
| `system/openloops` | system | open-loop extraction, `core/openloops.py` | v1 |
| `system/openloops-draft` | system | the follow-up draft, `loops/openloops.py` | v1 |
| `system/react` | system | the reaction judge, `core/react.py` | v1 |
| `system/self-extract` | system | the companion's own views, `core/beliefs/self_extract.py` | v4 |
| `system/views-conflict` | system | the view conflict check, `core/beliefs/views_conflict.py` | v1 |
| `system/views-implicated` | system | which views a flag implicates, `core/beliefs/views_implicated.py` | v1 |
