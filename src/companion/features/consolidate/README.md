# Consolidate (ADR 0019)

Keeps memory tidy without letting a model decide what the person is. Each night it rereads memories a week old, and when the memory pass writes a new memory it checks that against its nearest existing one.

**Status:** shadow (review by 2026-10-26, judged on closes and questions that match the owner's own review). `COMPANION_CONSOLIDATE`: `shadow` (default, logs only), `on` (acts), `off` (skips it, and with it the whole night's work: grouping, routine expiry and episodes). Runs nightly at 04:00 and at write time inside the memory pass.

## How it works

Two checks, both read three times by a small model (`READS = 3`, `loops/reads.py` `read_times`). A label or relation counts only when all three reads agree (`unanimous`). A failed read is never agreement, so the verdict becomes `mixed` and nothing follows from it.

**The nightly check** (`nightly` in `run.py`, called from `memory/nightly.py` at 04:00 local time, `NIGHTLY_HOUR` in `daemon.py`). A night missed while the bot was down is made up five minutes after the next start, and the whole night is skipped when the daily spend cap is reached.
- A memory of theirs is due when it has no earlier check by `system/memory-check` (any version) and its last support, or its start, is at least 7 days old (`SETTLED_DAYS`). The oldest 40 are read per night (`PER_NIGHT`).
- The judge gets today's date and the claim, and answers `keep`, `passing`, `out_of_date` or `overstated`. Every read is stored in `memory_checks` with the verdict and the prompt as `name@version`. Tables are in `store/sqlite/migrations/`, and checks are never deleted.
- Code then picks a plan (`plan_for`). A `passing` memory that is an everyday, surface memory and has faded from the card (`core/card.py` `faded`) is closed. A memory with sensitivity 2 or more (`HELD`) is never closed by code, and a `passing` or `out_of_date` or `overstated` verdict on it is a question for the owner. `out_of_date` and `overstated` on any other memory are questions. `keep` and `mixed` do nothing.
- In `on` mode the memory is retired through `loops/curate.py` `retire` with the reason "a passing moment, faded from the card (ADR 0019)". In shadow `log_would_close` records the decision "would close belief (shadow)" and closes nothing. The closing is a retirement, never a delete (ADR 0002).
- One line is logged per night: how many were read, closed or would be closed, how many questions, and the cost.

**The write-time pair check** (`SameCheck` in `run.py`, called from `_stored_as_evidence` in `memory/slow.py` for each new memory of theirs, never for the companion's own views).
- It embeds any memory that has no vector, embeds the new claim, and takes the single nearest existing memory. If the cosine score is under 0.55 (`GATE`) it stops and asks nothing.
- Otherwise `system/memory-pair` reads the pair (earlier, later) three times for one of `same`, `merge`, `distinct`, `replaces`, `contradicts`. The reads are stored in `memory_checks` with the other memory's id. If any read failed, nothing is recorded and the memory is stored as usual.
- Read `same` three times, the memory is not stored as new. In `on` mode its quote is added as evidence on the older memory and the decision "confirmed: the same as an existing memory, stored as evidence on it" is logged. In shadow the decision "would store as evidence on an existing memory (shadow)" is logged and the memory is stored as usual.
- Read `replaces` or `contradicts` three times, it is stored as usual and the pair is a question for the owner in `memory review` (keep one, the other, or both). Code never acts on a conflict. `merge` and `distinct` verdicts are stored but nothing reads them, since grouping is the merging feature's job.
- Any error in the check is logged as a warning and the memory is stored as usual.

**Questions for the owner.** `companion memory review` (`cli/memory.py`, shared with merging) lists unanswered checks: merges first, then `out_of_date`, `overstated` and held `passing` memories, then conflicting pairs. A pair that sits inside a pending merge is held back, since pieces of one moment often read as a conflict apart. A passing memory that is not sensitive is not asked about. Answers are stored in `memory_answers`. Retire, keep, keep one or keep both are the choices, and a retirement states the reason and which one the owner kept. Nothing is merged or closed by a question that was skipped.

Spend is tagged `consolidate`.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the prompts (`CHECK`, `PAIR`), the labels (`Label`, `Relation`), `verdict` (what counts as agreed), `plan_for` (close, ask or nothing), `HELD` |
| `run.py` | effects: the nightly check (`nightly`, `SETTLED_DAYS`, `PER_NIGHT`) and the write-time pair check (`SameCheck`, `GATE`) |
| `store.py` | its queries: `memory_checks` and `memory_answers`, append-only (tables in `store/sqlite/migrations/`) |

## Prompts

- `system/memory-check`: labels one memory `keep`, `passing`, `out_of_date` or `overstated`. A failed or unreadable read is None and the verdict is `mixed`.
- `system/memory-pair`: relates two memories as `same`, `merge`, `distinct`, `replaces` or `contradicts`. If any read fails, the pair is not recorded.

## Commands

- `uv run companion memory review`: answers the questions the check raised and the merge proposals, until you quit.
- `uv run companion merge ID ID --claim "..."`: merges memories by hand, keeping every quote.
- `uv run companion shadows`: lists the review date for this feature.

## Measured

- 2026-10-19: single memories read passing by all three reads were all ones the owner had retired (24 of 24), out of date 4 of 6, overstated 2 of 5. Pairs read `same` three times were redundant 9 of 10 times. Only those two cases may act on their own (`evals/CHANGELOG.md`).
- 2026-10-20: the pair judge read 14 of 14 invented corrections as a conflict, with 2 and 3 of 20 look-alikes on two runs. A draft v2 was dropped, so a conflict stays a question (`evals/CHANGELOG.md`).
- 2026-10-21: the write-time check had labelled 7 pairs `merge` with nothing acting on them, which led to the grouping feature (`evals/CHANGELOG.md`).

## Tests

`tests/features/consolidate/`
