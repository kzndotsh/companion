# Lore (ADR 0020)

Keeps what the companion likes the same from day to day. It sorts the views it states about itself, and shows back the few tastes that fit what they just said, so it does not invent a new favourite each time.

**Status:** live. `COMPANION_LORE`: `on` (default), `shadow` (logs what would be shown, shows nothing), `off`. Labelling runs after a memory pass that stored new views of its own, and from a command. The look-up and its note run before the reply, on ordinary turns only.

## How it works

**Labelling** (`label_views` in `run.py`, the `after_own` step of the feature, so it runs after each memory pass that stored new views of its own, and from `companion lore --label`). The views ledger mixes its own tastes with advice it gave, rules for how it treats the person, facts about what it is, and the odd claim of a lived event. Each view with no kind yet is sent to `system/lore-label` as `[vN] claim (it said: "quote")`, up to 60 per call (`BATCH`), and gets one of:
- `taste`: a personal preference of its own, a quirk, a small ritual.
- `stance`: advice or an opinion on a topic or on their situation.
- `rule`: how it treats them, or what it will and will not do.
- `self`: what it is or can do.
- `lived`: a claim that something happened to it in the world, or about a body or senses.

Each batch is read three times (`READS`, `loops/reads.py` `read_times`). A view is a `taste` only when every read says taste (`agreed`). Otherwise it takes the commonest other kind, or `stance` when no read gave one. If any read failed or was unreadable, nothing is stored for that batch and it waits for the next pass, never labelled from fewer reads. Labels are append-only: `--relabel` labels every current view again and the newest label wins. Spend is tagged `lore`.

**What lore is.** Only a `taste` is lore (`lore` in `logic.py`). A `lived` claim is never lore and never counted (A22).

**Showing it** (`tastes_for_turn`, the look-up, and `lore_offer`, the note). Only on an ordinary turn, which is `is_casual`: a listening read exists, severity 0, not in a pretend scene, and not a goodbye. The switch must not be `off` and an embedder must exist.
- `nearest_tastes` embeds their message, plus any taste with no stored vector in the same call, under a 2 second limit (`LOOK_SECONDS`). A slow or failed call shows no tastes this turn and logs a warning.
- It takes the nearest tastes by cosine score, at most 2 (`SHOWN`), and drops any below 0.3 (`GATE`).
- The note shows each as the words it said, `you said: "..."`, using the view's first quote, in the system block through `notes/lore`. It says these are its own, to keep to them if it comes up, and not to bring them up just to mention them.
- The decision "lore: its own tastes nearest their message" is logged with the view ids, scores and claims. In shadow its reason adds "(shadow)" and nothing is sent.

It does not check new tastes against old ones yet. A taste the owner thinks wrong is retired with `companion retire ID`.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the kinds (`Kind`), the prompt and parse (`prompt`, `parse`), what counts as agreed (`agreed`), which views are lore (`lore`), the note (`lore_note`), `SHOWN`, `GATE`, `BATCH` |
| `run.py` | effects: labelling (`label_views`), the nearest tastes (`nearest_tastes`, `LOOK_SECONDS`), the look-up and note as `LORE` |
| `cli.py` | `companion lore`: list its tastes and how its views are sorted, with `--label` and `--relabel` (`label_now`) |

Its queries (`view_kinds`, `add_view_kinds`, `self_beliefs`) are in `store/sqlite/store.py`.

## Prompts

- `system/lore-label`: gives each view one kind. A failed or unreadable read means the batch is not labelled and is tried again.
- `notes/lore`: in the system block on an ordinary turn when a taste of its own is near their message.

## Commands

- `uv run companion lore`: its tastes, newest first, with the words it said, and a count of how its views are sorted.
- `uv run companion lore --label`: labels its new views first (a model call).
- `uv run companion lore --relabel`: labels every view again (model calls).
- `uv run companion retire ID`: retires a view the owner does not want kept.

## Measured

- 2026-10-20: `system/lore-label` v1 labelled 78 views in one call for $0.0014, 19 tastes, about 17 of them its own by eye (`evals/CHANGELOG.md`).
- 2026-10-20: with the note, asked what music it likes went from 4/20 to 20/20 and favourite weather from 0/20 to 17/20, with ordinary turns 20/20 both ways, on five public fixtures at 20 samples (`evals/CHANGELOG.md`).
- 2026-10-20: three reads each on the 20 tastes, a taste only when all agree, because one live read had called advice a taste. A draft v2 was not made (`evals/CHANGELOG.md`).
- 2026-10-21: three live turns showed a taste at scores 0.303 to 0.322, none fit the moment and none was brought up. Too few to move the 0.3 gate (`evals/CHANGELOG.md`).

## Tests

`tests/features/lore/`
