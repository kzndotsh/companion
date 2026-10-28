# History (ADR 0025)

Keeps the small details of its own past that the companion makes up in chat, so it tells the same past every time. A pet it once named, a haircut, a habit, a small memory: each is picked out of its own messages, checked against the character sheet and the stories already kept, and kept as canon or not with a reason.

**Status:** step 1, shadow. `COMPANION_HISTORY`: `shadow` (default), `on`, `off`. Stories are captured and checked after each memory pass, and the look-up beside a turn logs what it would show. Nothing reaches the talker in step 1, so `on` behaves as `shadow` until step 2 adds a note. `off` reads nothing and logs nothing. Review by 2026-11-09 (`core/shadows.py`).

## How it works

**What counts** (the owner's decisions, ADR 0025):
1. Only stories it makes up while chatting. Nothing is generated between chats.
2. In a pretend scene, a small fact about itself said in passing counts (a stray it once named). Something that happens inside the scene's story does not.
3. Small everyday details only. A big life event (a past partner, family, a death, an illness, a trauma) is never canon unless the character sheet already has it.

**Capture** (`read_history` in `run.py`, run by the memory pass when the switch is not `off`). It keeps its own bookmark (`story_reads`), so it reads its own messages whatever the other passes did. Each pass reads up to 3 batches (`BATCHES`) of 40 messages (`BATCH`) past the bookmark, with the 4 before each for context, and sends the companion's messages as targets to `system/history-capture`, once. Each detail comes back with its message label, an exact quote, a third-person claim and a place: `its_past` or `scene`. Code (`to_story` in `logic.py`) keeps one only when:
- the label is one of the companion's own messages;
- the quote is in that message (the quote gate, `core/beliefs/verify.py`);
- the message is not a what-if (`hypothetical` frame);
- the place is `its_past`. In a `play` or `story` message that is a fact said in passing; a `scene` detail is dropped with its reason.

A kept story carries the quote, the companion as speaker and the message's frame (ADR 0001, 0010). Every drop and every keep is a logged decision (`history: a story dropped`, `history: a story of its own past recorded`). A failed or unreadable capture leaves the bookmark where it was, so the batch is read again next pass. The same quote from the same message is never stored twice. It never reads or changes what is stored about the user, and it does not use the views ledger: `system/self-extract` drops anything said in a scene and anything it says it felt or experienced, so most stories never become views.

**The canon check** (`_check` in `run.py`). After capture, up to 10 waiting stories (`CHECKS`), oldest first, are each sent to `system/history-canon` with the character sheet (the sheet without its roleplay and crisis sections) and every story already canon under a label (`s1`, `s2`). Each is read three times (`kit/reads.py` `read_times`, spend `history`), because one read decides whether a detail becomes permanent. Each read gives one verdict, and code turns the three into a standing (`rule` in `logic.py`):

| Reads | Standing | Reason (written by code) |
|---|---|---|
| all `fits`, or no majority for one `same` | `canon` | fits the sheet and the stories kept so far |
| most reads `same` as one kept story, none objecting | `evidence` of that story | the same story as `id`, kept as a telling |
| any `contradicts` | `not_canon` | contradicts `id` ("claim"), or contradicts the character sheet |
| any `too_big` | `not_canon` | a big life event the character sheet does not have |
| any `not_a_story` | `not_canon` | not a story about its own past |

One objecting read keeps a story out of canon. When reads object differently, the commonest objection wins, and a tie goes to `too_big`, then `contradicts`. A `same` with no kept story named is an unreadable read. If any read failed or was unreadable, nothing is recorded and the story waits for the next pass. It is never ruled from fewer reads. Each ruling is a logged decision (`history: the canon check ruled`).

**Append-only.** Stories, events, vectors and the bookmark are never updated or deleted (ADR 0002). A story's standing is its newest event. `companion retire ID` adds a `retired` event with the owner's reason, so a retired story leaves canon and stays listed.

**Showing it, in shadow** (`stories_beside`, the feature's `shadow` look-up, run beside the turn after the reply). Only on an ordinary turn (`is_casual`: not serious, not in a scene, not a goodbye), with an embedder.
- `nearest_stories` embeds their message, plus any canon story with no stored vector in the same call, under 2 seconds (`LOOK_SECONDS`). It stores the new vectors (`story_vectors`). A slow or failed call logs a warning and nothing else.
- It takes the nearest canon stories by cosine score, at most 2 (`SHOWN`), and drops any below 0.3 (`GATE`), as lore does.
- It logs `history: its canon stories nearest their message (shadow)` with each story's id, score and claim; how many times it was told (the first telling and each kept as evidence); when it was last told; and whether a telling is still among the 40 messages the talker reads (`in_view`). The reason counts the ones told before and out of view, which a step 2 note could mark as told before so it is not told as new. Nothing is sent.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the kinds (`Place`, `Verdict`, `Standing`), a story and its record (`Story`, `Recorded`), the capture parse and its rules (`parse_capture`, `to_story`), the canon prompt, parse and ruling (`canon_prompt`, `parse_canon`, `rule`), the nearest stories (`nearest`), `SHOWN`, `GATE` |
| `run.py` | effects: capture and the canon check after a memory pass (`read_history`, `pass_step`), the look-up beside a turn (`nearest_stories`, `stories_beside`), and `HISTORY` |
| `store.py` | its tables behind `Store.stories()` (`Stories`): stories, events, vectors and the bookmark |
| `cli.py` | `companion history`, and retiring a story (`retire_story`, used by `companion retire`) |

The tables are in `store/sqlite/migrations/0036_history.sql`.

## Prompts

- `system/history-capture`: the details of its own past in its own messages, each with a quote, a claim and whether it is its own past or happens in a scene.
- `system/history-canon`: one story against the character sheet and the stories kept as canon: fits, same, contradicts, too big or not a story.

## Commands

- `uv run companion history`: canon stories with how many times each was told, the ones waiting for the check, the ones kept as a telling of an earlier story, the ones not canon with the reason, and the retired ones.
- `uv run companion retire ID`: retires a story by id prefix when no current belief has that prefix.

## Measured

Nothing yet. The owner's session measures both prompts on made-up fixtures before the review, and the review reads a fortnight of rulings by eye.

## Tests

`tests/features/history/`, and the memory pass running the step in `tests/memory/test_memory_pass.py`.
