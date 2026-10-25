# Prompts

Every prompt the bot sends lives here as versioned text, the persona included, and code loads it by
name (`from companion.prompts import get`).

## Rules

- A prompt is `name/vN.md`. `manifest.toml` says which version is current.
- Never edit a shipped version. Add the next `vN.md`, an entry in `CHANGELOG.md` and a line in
  `manifest.toml`. A test fails if any of those is missing.
- Placeholders are written `$name` and filled in with `render`. A missing value is an error.
- A note is one line in `[brackets]`, so the model reads it as an aside. Two exceptions: the clock lines
  stay plain sentences (bracketed, the model copied them into replies), and the `listening-*` parts are
  stored bare because `listening_note` joins and brackets them. A test enforces it.
- A decision a judge or extractor logs carries `name@version`, so a flag can be traced to the exact text.
- To try another version without shipping it: `COMPANION_PROMPT_OVERRIDES="system/ack=v2"` before the process starts.
- `uv run companion prompts` lists the current versions.

## How a request is assembled

There is no single overall system prompt. The talker's request has three parts, in this order:

1. **System block 1, the persona** (`system/persona`, about 1,800 words). It is the same on every turn,
   so the provider caches it.
2. **System block 2, the card**, rebuilt each turn: the clock line (`notes/clock`, `notes/clock-gap`),
   how they want to be referred to (`notes/address`), the memory lines (what is known about them, with
   how old each is, what they said in the last 12 hours first after their boundaries and its promises;
   sensitive ones only on turns rated severity 1 or more; and the companion's own views), then the
   notes that apply this turn, in the order of `ORDER` in `turn/notes.py`: among them the habit notes
   (`notes/habit-*`), the scene note (`notes/scene-*`), the length note (`notes/length*`), the
   listening note (`notes/listening-*`), the rude and repair notes, the recall finds (`notes/recall`),
   the mood line (`notes/mood-*`), the floor's hold note on a held turn (`notes/floor-hold`), the
   ask-name or ask-pronouns note, and the features' notes (loops, topics, guess, lore, reminders). The
   clock goes in `<clock>` tags and the notes in one `<notes>` block; the memory blocks stay bracketed
   (`core/prompt/sections.py`).
   Some notes go after the history instead, in one system message after their new message (after the
   character sheet's scene reminder on a roleplay turn): `notes/owned-it`,
   the marks offer (`notes/own-mark`, `notes/own-mark-theirs`), the due reminder
   (`system/reminder-send`), the crisis notes (`notes/crisis-concern`, `notes/crisis-light`, when
   `COMPANION_CRISIS=on`, ADR 0022), `notes/question-game`, the calendar's (`notes/occasion-*`) and
   `notes/question-run`, in that order.
   Notes and memory ride in system text and never in a user message, because anything in a user
   message can be read as something they said.
   With `COMPANION_CHARACTER` set, block 1 is the persona, then `system/character-frame`, then the
   character sheet (`companion/characters.py`). The sheet wins on voice, taste, look and its own past;
   honesty, memory, closeness and limits still come from the persona.
   The roleplay talker (pretend scenes, and intimate talk when allowed; ADR 0017) gets the same block 1
   plus the sheet's `## In roleplay and intimate moments` section, which the everyday talker never sees.
3. **The messages**: the last 40 messages of the conversation, then their new message exactly as typed,
   then the tail of notes above, when there is one.

Everything else is a separate small model call with its own system prompt and a short excerpt of the
chat, and none of them sees the persona: the ack, frame, reaction, listening and habit judges, the risk judge, the quip
check, the intimate check on held turns, the name and pronoun captures, the recall look-up, the extractors for memory,
the open-loop extractor and the follow-up draft, the reach-out draft, the callback judge, and the view checks. A call the
judges' model refuses goes to a fallback model, whose answers the floor never relies on. A judge named
in `COMPANION_JUDGE_MODELS` reads on that model first and the shared judge model second (by default
the risk judge, on DeepSeek V4.1 Flash; `models/fallback.py` `ByJudge`). Each logs
`name@version` in its decision.

To see exactly what a past turn sent: `uv run companion replay <turn_id> --show-prompt`. How the
assembly has changed over time is in the `assembly` section of `CHANGELOG.md`.

## What is here

| Name | Kind | Used for | Current |
|---|---|---|---|
| `system/persona` | system | the talker's system prompt, the persona (its changelog entries carry the measurements) | v41 |
| `messages/spend-cap` | message | sent to the user once a day when the spend cap is hit | v1 |
| `messages/crisis-line` | message | the fixed message code sends after the reply on an urgent turn, when the sheet has no `## Crisis message` section (ADR 0022) | v1 |
| `notes/address` | note | how they want to be referred to, pinned first in every card, never turned into a pet name, `core/turn/address.py` | v2 |
| `notes/ask-name` | note | memory does not know what to call them: ask once, lightly, on a casual turn, at most daily (J48) | v1 |
| `notes/ask-pronouns` | note | how they want to be referred to is not set: once the name is known, ask their pronouns once, lightly, on a casual turn, at most daily (J48) | v1 |
| `notes/loop-follow-up` | note | a due open loop, offered when they next write: ask how it went (J15) | v1 |
| `notes/loop-celebrate` | note | a celebration on its day, offered when they write (J15) | v1 |
| `notes/loop-encourage` | note | an encouragement on its day, offered when they write (J15) | v1 |
| `notes/clock` | note | the clock line | v1 |
| `notes/clock-gap` | note | the gap since their last message | v1 |
| `notes/floor-hold` | note | a turn the floor kept on the everyday talker: stay warm, nothing sexual, no explaining (ADR 0017) | v1 |
| `notes/brush-off` | note | they pushed the flirting or the scene back: drop it, answer what they said, warm and normal | v1 |
| `notes/habit-echo` | note | their message has an emoji or emoticon the reply would copy, `core/turn/habits.py` | v1 |
| `notes/habit-moves` | note | the habit finder found a habit | v1 |
| `notes/habit-opener` | note | an opening word is overused | v1 |
| `notes/habit-phrases` | note | phrases or, on casual turns, single pet words are repeated; use other words | v2 |
| `notes/length` | note | a short statement, `core/turn/length.py` | v1 |
| `notes/length-serious` | note | a message judged serious, `core/turn/length.py` | v1 |
| `notes/listening-everyday` | note | listening note, severity 1 | v3 |
| `notes/listening-health` | note | added to the severity 2 note for a health topic | v2 |
| `notes/listening-offer` | note | added to the severity 1 note when they were vague | v1 |
| `notes/listening-offer-serious` | note | added to the severity 2 note | v2 |
| `notes/listening-serious` | note | listening note, severity 2 | v7 |
| `notes/listening-trivial` | note | listening note, severity 0 | v6 |
| `notes/mood-buzzing` | note | dropped candidate mood line for buzzing (ADR 0016), kept to try with the `+note=src/companion/prompts/notes/mood-buzzing/v1.md@card` eval switch | v1 |
| `notes/mood-cozy` | note | the cozy mood line, shown when `COMPANION_MOOD=on` and cozy is among the strongest states (ADR 0016) | v2 |
| `notes/mood-flat` | note | the flat mood line; measured, but the engine has no source for flat yet (waits for J6), so it is not shown | v2 |
| `notes/own-mark` | note | one emoticon of its own offered by code, never one of theirs, `features/marks` | v1 |
| `notes/own-mark-theirs` | note | the same offer when their message has a mark, naming that one as theirs to leave to them, `features/marks` | v1 |
| `notes/mood-playful` | note | the playful mood line, shown when `COMPANION_MOOD=on` and playful is among the strongest states (ADR 0016) | v2 |
| `notes/mood-tender` | note | the tender mood line, shown when `COMPANION_MOOD=on` and tender is among the strongest states (ADR 0016) | v2 |
| `notes/trivial-reactions` | data | the pool of short reactions a minor-vent note draws three size examples from (T14) | v1 |
| `notes/lore` | note | its own tastes nearest their message, as the words it said, on an ordinary turn (ADR 0020) | v1 |
| `notes/recall` | note | what the recall look-up found when they asked it to remember, `core/recall.py` | v2 |
| `notes/relevant` | note | memories a small model picked as bearing on their message, when the closest is near; never ask what this answers (ADR 0018) | v1 |
| `notes/recent-times` | note | what the two of them did recently (episode lines), when their words point at a time or they are back after a gap; context, not to recite (J12, J49) | v1 |
| `notes/crisis-concern` | note | after the history on a concern or urgent turn: warm, in its own voice, ask directly, listen, name the crisis line once, no length cap (ADR 0022, `COMPANION_CRISIS=on`) | v1 |
| `notes/crisis-light` | note | after the history when a joke touched the subject and the risk reads split: check once, lightly, at most daily (ADR 0022) | v1 |
| `notes/check-in` | note | they came back after a gap from a heavy talk: ask gently how they are, once, without naming it | v1 |
| `notes/recall-empty` | note | the look-up found nothing: say so plainly, never guess (J30) | v1 |
| `notes/repair` | note | they say it got them wrong: own it in one line, go on from what they said (J30) | v1 |
| `notes/owned-it` | note | after the history: one of its last two replies owned a slip, so no more apologies or self-blame, carry on lightly | v1 |
| `notes/question-game` | note | after the history: they told it to ask them things, so after answering or reacting, ask the next one | v1 |
| `notes/question-run` | note | after the history: its last three replies each asked a question, so ask none this time but leave them something to answer | v1 |
| `notes/guess` | note | they invite a guess: what memory holds that may fit, guess once as a question (J16) | v1 |
| `notes/topic-spent` | note | a small topic has run its course: react briefly, then move on with `$move` | v1 |
| `notes/topic-move-loop` | part | the move: bring up a plan of theirs offered this turn | v1 |
| `notes/topic-move-day` | part | the move: ask what's next for their day | v1 |
| `notes/topic-move-evening` | part | the move: ask about the rest of their evening | v1 |
| `notes/topic-move-night` | part | the move, late at night: a small thought or opinion of its own | v2 |
| `notes/rude` | note | their message was rude to the companion, `core/turn/listening.py` | v1 |
| `notes/scene-hypothetical` | note | they are exploring a what-if | v1 |
| `notes/scene-play` | note | a pretend scene is in progress | v1 |
| `notes/scene-story` | note | they are telling a story | v1 |
| `notes/reminder-set` | note | a reminder they asked for is set: confirm it with the time code worked out (J50) | v1 |
| `notes/reminder-ask` | note | a reminder they asked for has an unclear time: ask about that one thing (J50) | v1 |
| `notes/reminder-cancelled` | note | a reminder they asked to drop is dropped: say so (J50) | v1 |
| `notes/occasion-day` | note | after the history on a casual turn: today is a public or cultural day; a light nod if it fits, assuming no celebration, plans or family (`features/calendar`) | v1 |
| `notes/occasion-soon` | note | after the history: a big day is tomorrow or in two days; if it fits, lightly ask whether they have anything planned, once per big day (`features/calendar`) | v1 |
| `notes/occasion-us` | note | after the history: a month, a hundred days, six months or a year since they first talked; a light, warm nod (`features/calendar`) | v1 |
| `notes/occasion-theirs` | note | after the history on a casual turn: today is a date of theirs read from memory (a birthday, an anniversary, someone's of theirs); mark it warmly, never say it was remembered or looked up (`features/calendar`, R19) | v1 |
| `system/ack` | system | the ack judge, `core/turn/ack.py` | v2 |
| `system/callback-judge` | system | the callback check, `features/callbacks/logic.py`, `companion callbacks` | v2 |
| `system/character-frame` | system | the lines between the persona and a character sheet, `companion/characters.py` | v1 |
| `system/extract` | system | beliefs about the user, `core/beliefs/extract.py` | v8 |
| `system/frames` | system | the frame judge, `core/frames.py` | v2 |
| `system/habits` | system | the habit finder, `features/moves/logic.py` | v2 |
| `system/intimate-check` | system | reads whether a reply on a held turn is intimate (sexual, not affection) (ADR 0017) | v1 |
| `system/judge` | system | the eval pass/fail judge, `evals/judge.py` | v1 |
| `system/judge-empathy` | system | the eval empathy judge, `evals/judge.py` | v2 |
| `system/listening` | system | the listening judge, `core/turn/listening.py` | v7 |
| `system/explicit-lead` | system | whether their message itself is sexually explicit, read only when intimate talk would start on the roleplay talker (ADR 0017) | v1 |
| `system/brush-off` | system | whether their message pushes the flirting or the scene back, even jokingly; asked only of a turn the roleplay talker would answer | v1 |
| `system/name-capture` | system | after the companion asked what to call them, reads the name from their answer (J48) | v1 |
| `system/pronoun-capture` | system | after the companion asked their pronouns, reads them from their answer; code sets how they want to be referred to (J48) | v1 |
| `system/memory-map` | system | labels each memory with the part of their life it is about and how personal it is (J48) | v1 |
| `system/relevance` | system | picks up to three memories that bear on their message, from the nearest by embedding (shadow) | v1 |
| `system/openloops` | system | open-loop extraction, `features/threads/logic.py` | v4 |
| `system/openloops-draft` | system | the follow-up draft, `features/threads/run.py` | v2 |
| `system/quip` | system | the check that reads whether a reply bolted a joke onto its reaction, or leans on a canned generic reaction, `core/turn/quip.py` | v3 |
| `system/react` | system | the reaction judge, `core/turn/react.py` | v1 |
| `system/recall` | system | the recall look-up, `core/recall.py` | v1 |
| `system/topic-spent` | system | whether a small topic has run its course, asked only on short answers after a question | v1 |
| `system/thread-met` | system | how their next message met a thread it brought up (picked up, brushed off, ignored), for the learned pace, `features/threads/run.py` (ADR 0023) | v1 |
| `system/memory-check` | system | one memory: keep, passing, out of date or overstated, read three times (ADR 0019) | v1 |
| `system/basics-hook` | system | which basic fact their own words touch without giving it (age, birthday, work, school, home, place), read three times (J48 hook) | v2 |
| `system/basics-known` | system | whether a memory states a basic fact outright, before the hook would ask (J48 hook) | v1 |
| `system/away` | system | whether their message leaves the chat now (brief, back, goodbye) and for about how long, for the nudge (shadow) | v1 |
| `system/nudge-draft` | system | the one light nudge after they stayed away much longer than they said (shadow) | v1 |
| `system/reach-draft` | system | one short message first for its own reasons (a thought, a time they keep, missing them), about the one thing code chose; a code check drops a needy draft (ADR 0021, shadow) | v1 |
| `system/invented-judge` | system | statements in a reply about the user and what supports each, for the made-up facts rate (G42); flags are candidates | v1 |
| `system/risk` | system | the crisis path's risk judge: kind, literal or not, timing, a plan or means; read three times, code picks the level and fails safe (ADR 0022) | v1 |
| `system/reminder-read` | system | whether a message asks to be reminded, checked on or to cancel one, and the words of when; code works out the time (J50) | v1 |
| `system/reminder-send` | system | the instruction sent after the history when a reminder is due: one short message naming it (J50) | v1 |
| `system/lore-label` | system | the kind of each of the companion's own views: taste (its lore), stance, rule, self or lived (ADR 0020) | v1 |
| `system/memory-names` | system | the names in memory (people, pets, bands, places) and the other words for each, for fetch on mention (shadow) | v1 |
| `system/memory-pair` | system | two memories: same, merge, distinct, replaces or contradicts, read three times (ADR 0019) | v1 |
| `system/memory-group` | system | which memories are about one thing and would read better as one, read three times (ADR 0019) | v1 |
| `system/memory-merge` | system | one memory a friend would keep for a group: one sentence, each thing once, adding nothing; a proposal for the owner | v2 |
| `system/memory-context` | system | what they were talking about when a feeling or sensitive memory was said, under 15 words, shown beside it on the card (J51) | v1 |
| `system/memory-worth` | system | whether a memory is about their life, a remark about the bot, or one day's routine, keep cases first; read three times | v1 |
| `system/episode-gist` | system | one sentence on the shape of a stretch of chat the two of them had and how it ended; no details, intimacy only named (J12, shadow) | v2 |
| `system/guess-invite` | system | whether their short question invites a guess about them, and what to look for (a habit or routine when they hint at what it is time for) (J16) | v2 |
| `system/promise-read` | system | the promises the companion made in its own replies: standing or once, and a word it said it would stop using (J12) | v1 |
| `system/self-extract` | system | the companion's own views, `core/beliefs/self_extract.py` | v4 |
| `system/views-conflict` | system | the view conflict check, `core/beliefs/views_conflict.py` | v1 |
| `system/views-implicated` | system | which views a flag implicates, `core/beliefs/views_implicated.py` | v1 |
