# Focus

Ranks the memory card by what the moment is about. Without it the card held the same memories every turn, by kind and by how recently each was mentioned, whatever the topic.

**Status:** live. `COMPANION_FOCUS`: `on` (default) or `off`. It runs before the reply on every turn, scenes included.

## How it works

The look-up (`focus_for_turn`, the feature's `look`) embeds their message alone and together with the companion's last reply (`moment_texts`), after filling any memory with no vector yet (`kit/embed.py`). Each memory's closeness is its best cosine score against either (`closeness`). It returns a `Focus` (the scores and the vectors, `core/card.py`), which the assemble stage hands to `build_card`. The whole look-up has a 2 second limit (`LOOK_SECONDS`, `kit/embed.py`); a slow or failed one logs a warning and the card is built the old way.

With a focus, the card keeps their boundaries and its promises first, then fills the other places (15 in all) with the closest memories (`_focused` in `core/card.py`):
- a memory within 0.90 of one already chosen is skipped (`FOCUS_SAME`), so one fact stored in several wordings takes one place;
- a guarded memory (sensitivity 2 or more) only when they are sharing and it scores at least 0.40 (`FOCUS_GUARDED`);
- a mildly personal one (sensitivity 1) only at 0.35 or more (`FOCUS_PERSONAL`);
- a place nothing fills stays empty, and the rest are logged as crowded out.

Freshness still applies first: stale and faded memories are not ranked. Each turn logs `card: by focus` with the closeness of each memory shown. Spend is tagged `focus` (the message) and `relevance` (new memories' vectors).

## Files

| File | What |
|---|---|
| `logic.py` | pure: what is embedded, each memory's closeness, the time limit |
| `run.py` | effects: the look-up, and the `Feature` (`FOCUS`) |

## Prompts

None.

## Commands

None. Read it in the decision log (`card: by focus`).

## Measured

- 2026-11-02: an audit of 150 turns found the card held 80 distinct memories across 371 turns, four of them on every card. The 150 cards rebuilt both ways and compared by three blind Claude Sonnet judges: topic-ranked 131, as before 8, tie 11. Lists judged, not replies (`evals/CHANGELOG.md`, [issue #35](https://github.com/kzndotsh/companion/issues/35)).

## Tests

`tests/features/focus/` and `tests/core/test_card_focus.py`.
