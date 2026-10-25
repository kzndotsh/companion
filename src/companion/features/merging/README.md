# Merging (ADR 0019)

Finds memories about one thing (one moment split into pieces, one interest restated) and proposes each group as a single memory. The memory pass often splits a moment into several memories, and this puts them back together for the owner to approve.

**Status:** live as proposals only, and nothing is merged without the owner. No switch of its own: the nightly grouping step always runs, even when `COMPANION_CONSOLIDATE=off` skips the nightly memory check (see consolidate). Runs nightly at 04:00 local time (`memory/nightly.py`, after the memory check) and from a command.

## How it works

**Grouping.** `propose` in `run.py` takes a list of memories and lists them for the judge as `[m1] (date) claim | their words: "quote"`. `system/memory-group` reads the list three times (`READS = 3`) and each read returns groups of labels. `agreed` in `logic.py` keeps a pair only when all three reads put it together, then joins overlapping pairs into groups. A failed or malformed read means no groups at all, never a partial agreement. A group needs two or more members.
- The nightly run (`recent`, called from `memory/nightly.py`) takes the memories of theirs recorded in the last two days (`RECENT_DAYS`), splits them by local day, and groups each day on its own.
- `companion memory group` (`everything`) groups every day of the whole store, then the whole store at once, to catch repeats across days. One list can be long, and a day's list refused by the first model was read by the fallback.
- A group already proposed (same set of members, whatever the answer) is not proposed again.

**Wording.** For each new group `system/memory-merge` is called once with the members and writes one plain sentence about the user, third person, at most 30 words, keeping a few examples. It may set `keep_apart` instead, and then no proposal is stored. A failed call or an empty claim also stores nothing, and a warning is logged. The proposal is stored in `merge_proposals` with its members, the wording and the prompt as `name@version`.

**The owner's answer.** `companion memory review` (`cli/memory.py`, shared with consolidate) asks merge proposals first, before the checks, and holds back a conflict between two pieces of a pending merge. The choices are merge, pick which belong, word it yourself, keep apart, note why, skip. Answers are stored in `merge_answers`.
- Merge or word it yourself calls `loops/curate.py` `merge`: one new memory carrying every quote of the originals, which are closed as merged, never removed (ADR 0002). Its kind is `merged_kind`: a state if any member is a passing state, so it keeps fading, else the first member's kind. Sensitivity and confidence are the highest of the members.
- Pick records which members belong together, by number. The next nightly or `group` run calls `repick`, which writes the wording for just those members and proposes them again alone (if every member is still current and that set was not asked before).
- A note keeps the proposal open for another time. Keep apart closes it. A proposal whose memories have since closed is marked gone.

Spend is tagged `consolidate`, which is also the name `COMPANION_JUDGE_MODELS` uses to route the three grouping reads (the wording call uses the shared judge model). The grouping judge can propose looser groups, such as two related likes, and those are the owner's to keep apart.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the prompts (`GROUP`, `WRITE`), `listing`, `read_groups`, `agreed` (what counts as a group), `read_claim`, `merged_kind` |
| `run.py` | effects: `propose`, `repick`, the last two days each night (`recent`, `RECENT_DAYS`), the whole store (`everything`) |
| `store.py` | its queries: `merge_proposals` and `merge_answers`, append-only (tables in `store/sqlite/migrations/`) |
| `cli.py` | `companion memory group` (`group_now`) |

## Prompts

- `system/memory-group`: groups memories about one thing, answering with lists of labels. A failed or malformed read means no agreement, so no group.
- `system/memory-merge`: writes the one merged sentence, or `keep_apart`. A failed call or an empty claim stores no proposal.

## Commands

- `uv run companion memory group`: proposes merges across every day and the whole store, and prints how many and the cost.
- `uv run companion memory review`: answers the merge proposals and the memory checks.
- `uv run companion merge ID ID --claim "..."`: merges by hand, keeping every quote.

## Measured

- 2026-10-21: `companion memory group` on the live store proposed 52 merges (sizes 2 to 6) for 2.1 cents. By eye the groups were right, a few looser ones are the owner's to keep apart (`evals/CHANGELOG.md`).

## Tests

`tests/features/merging/`
