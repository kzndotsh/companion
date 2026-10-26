# Scene memory (ADR 0026)

A separate memory lane for intimate scenes. Memories about sex and intimate play are kept apart from everyday ones: a scene turn gets its own card (their limits, what they are into nearest the moment, perhaps one thing they are curious about, and what they are called), and every other turn leaves the intimate lane out.

**Status:** shadow. `COMPANION_SCENE_MEMORY`: `shadow` (default), `on`, `off`. In `shadow` the memory pass places memories and reads scenes, and each turn logs the scene card it would send and the intimate memories it would leave off the everyday card; the request is unchanged. `on` sends the scene card on a turn the roleplay talker answers and leaves the intimate lane off every other turn's card and the relevance look-up. `off` reads nothing, logs nothing and changes nothing. Review by 2026-11-09 (`core/shadows.py`).

## How it works

**The owner's decisions** (ADR 0026):
1. It learns from both what they say about it outside a scene (the memory pass's own extraction) and how they play inside scenes. A pattern from play counts only once seen in two separate scenes, and it is only ever shown on scene turns.
2. A scene turn keeps the basics (what they are called, and how they want to be referred to, which is pinned on every turn) and no other everyday memory.
3. It may bring up something they said they are curious about, not only what they are into. Never a limit.

**Placing memories** (`label_lanes` in `run.py`, run by the memory pass when the switch is not `off`). Each pass takes up to 60 memories (`BATCH`) that may be stated as true (`is_assertable`) and have no place yet, and sends them to `system/scene-lane` three times (`read_times`, spend `scene memory`). Each read gives each memory a lane, everyday or intimate, and an intimate one a stance: `into`, `curious`, `hard_limit`, `soft_limit`, `style` or `aftercare`. Code turns the three reads into a place (`agree` in `logic.py`): the lane and stance all three gave, or `excluded` as doubt when they differ or a read left the memory out. A failed or unreadable read places nothing, and the batch waits for the next pass.

**The floor** (`screen` in `logic.py`), over the agreed place, in code, whatever the reads said. An everyday memory stays everyday. An intimate or doubtful one is kept out of scenes:

| Reason | When | Shown by `companion scene` |
|---|---|---|
| `floor` | its claim or a quote touches age, minors, school or an age-regression headspace (`touches_age`, a conservative word check), or it came from a turn the minor check held (a `minor check` decision with `minor` true) | the id only |
| `crisis` | sensitivity 3 | the claim and the reason |
| `listening` | it came from a turn the listening judge read as serious (severity 2 or more): said while they were sharing something heavy | the claim and the reason |
| `not_their_words` | a limit whose memory is not stated, real-frame and their own words | the claim and the reason |
| `doubt` | the three reads did not agree | the claim and the reason |

The age check is deliberately broad: it also matches a number under 18 that is not part of a date or a time, and the word "little" on its own, so a memory such as "likes it a little rough" is kept out too. A false match only costs a scene entry. The floor is applied when a memory is placed and again every time a scene card is built, over every turn its quotes came from, so a later confirmation from a held turn is caught. Only the newest place counts (`scene_lanes`, append-only).

**Patterns from scenes** (`read_scenes` in `run.py`). It keeps its own bookmark (`scene_reads`). Each pass reads up to 400 messages past it (`READ`) and cuts them into scenes as `core/frames.py` does: a scene starts at a message of theirs in play and holds the replies after it, and ends at a message of theirs out of play or after a two-hour gap (`scenes`). Up to 3 ended scenes a pass (`SCENES`, `closed`) are read, oldest first:
- A scene with any turn the minor check held is never read; `scene memory: a scene left unread by the floor` is logged with no text.
- `system/scene-pattern` gets the patterns already noted (p1, p2) and the scene's messages (m1, m2), once. Each pattern comes back with the noted one it repeats or none, a claim, a stance, their message's label and a quote.
- Code keeps one only when the message is theirs and in play, the quote is in it, the stance is `into`, `style` or `curious`, and nothing touches age (`refuse`). A limit is never taken from play. Each drop is logged (`scene memory: a pattern dropped`), without the text when the floor dropped it.
- A repeat adds that scene's quote to the noted pattern, once per scene; a new one is stored with its first quote. Each is logged (`scene memory: a pattern noted`) with how many scenes it has been seen in.

A pattern becomes an entry only once its quotes come from two separate scenes (`MIN_SCENES`, `pattern_entry`). A failed or unreadable read leaves the bookmark before that scene, so it is read again next pass. A batch that ends mid-scene leaves that scene for later, so one long scene never counts as two.

**The scene card** (`scene_lane` in `run.py`, called by `turn/assemble.py`). On a turn the roleplay talker answers (a pretend scene, or intimate talk the operator lets it answer; never a turn the floor held or one where they pushed back), code builds:
1. every current limit, hard first, then soft (`notes/scene-limits`);
2. at most 3 entries nearest the moment that say what they are into, how they like it to go, or what they want after (`NEAREST`, `notes/scene-known`);
3. at most one curious item, the nearest one, which it may invite once (`notes/scene-offer`);
4. the memories that say what they are called (`names_them` in `core/turn/address.py`, `notes/scene-basics`).

It goes in the system block in place of the memory card (ADR 0012), with none of the everyday card and none of its own views. How they want to be referred to stays pinned, as on every turn.

"Nearest" comes from the look-up before the reply (`nearest_for_turn`, the feature's `look`): on a turn in a pretend scene, or an intimate turn the operator lets the roleplay talker answer, it embeds the reply before their message with their message, plus any entry with no vector yet in the same call, under 2 seconds (`LOOK_SECONDS`), and scores every entry by cosine. New vectors are kept (`belief_embeddings` for memories, `scene_vectors` for patterns). A slow or failed look-up leaves only the limits and the basics.

**The curious item** is offered only when this turn's brush-off read answered and said no (a `brush-off` decision with `declines` false and a scorer), and never an item offered in the last 3 days (`COOL`) whose next brush-off read, on a later turn, said they pushed back (`cooled`). With `on`, each offer is logged once the turn is stored (`scene memory: a curious item offered`), which is what the next check reads.

**Every other turn.** The memories placed `intimate` are logged when the everyday card would hold them (`scene memory: intimate memories left off the everyday card`). With `on` they are left off the card, out of what the notes may state as true, and out of the relevance look-up (`features/relevance`, `hidden`). A memory kept out of scenes stays on the everyday card as before.

**Logged.** Each scene turn logs `scene memory: the scene card` with the ids of its limits, the nearest with their scores, the offer, how many basics, whether the look-up scored it, whether it was sent, and its text. The reason is written by code.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the lanes, stances and reasons (`Lane`, `Stance`, `Why`, `Place`), the floor (`touches_age`, `screen`), the lane prompt, parse and agreement (`lane_prompt`, `parse_lanes`, `agree`), scenes and patterns (`scenes`, `closed`, `Pattern`, `pattern_prompt`, `parse_patterns`, `refuse`, `pattern_entry`), the card (`Entry`, `scene_card`, `render_scene`) and the cooling (`cooled`) |
| `run.py` | effects: the pass step (`label_lanes`, `read_scenes`, `pass_step`), the entries (`entries`), the look-up (`nearest_for_turn`), the turn's lane (`scene_lane`), and `SCENE` |
| `store.py` | its tables behind `Store.scene_memory()` (`SceneMemory`): places, patterns and their quotes and retires, vectors, the bookmark, and the floor's facts about a message's turn (`facts`) |
| `cli.py` | `companion scene`, and retiring a pattern (`retire_pattern`, used by `companion retire`) |

The tables are in `store/sqlite/migrations/0037_scene_memory.sql`.

## Prompts

- `system/scene-lane`: each memory's lane, everyday or intimate, and an intimate one's stance.
- `system/scene-pattern`: how they tend to play intimate scenes, from one ended scene, quoted from their own messages.
- `notes/scene-limits`: the scene card's limits, hard and soft.
- `notes/scene-known`: the entries nearest the moment.
- `notes/scene-offer`: the one curious item it may invite.
- `notes/scene-basics`: what they are called.

## Commands

- `uv run companion scene`: the intimate lane by stance with quotes and how many quotes or scenes each has, the patterns seen in one scene so far, what is kept out of scenes with the reason (only the id for the floor), and the retired patterns.
- `uv run companion retire ID`: retires a memory by id prefix as before, or a pattern when no current memory or story has that prefix.

## Measured

Nothing yet. The owner's session measures the two judges on made-up fixtures and the scene card's notes on replies before the review, and the review reads the logged scene cards by eye.

## Tests

`tests/features/scene_memory/`, the turn in `tests/turn/test_scene_memory_turn.py`, and the switch in `tests/test_startup_line.py`.
