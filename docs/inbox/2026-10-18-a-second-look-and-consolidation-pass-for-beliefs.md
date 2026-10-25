# A second-look and consolidation pass for beliefs

**Status (2026-10-25):** partly built: the nightly memory check and write-time pair check run in shadow (ADR 0019, `src/companion/features/consolidate/`, with `merging`); corrections superseding their target are not built, card A15.

Added 2026-10-18 by the owner's idea: a loop that goes back over memory, corrects beliefs the first pass
got wrong once it has more context, and merges overlapping ones into grouped summaries or insights.

## What was measured first

Read-only audit, 2026-10-18 (details and rerun in `evals/CHANGELOG.md`). 187 live beliefs after four
days, none ever superseded. 40 sampled (sensitivity 3 left out), each judged by Sonnet 5.5 with the
messages around its quote and every other live belief in view: 30 correct, 6 overstated, 3 trivial,
1 wrong, 0 duplicates. Checked by eye, the verdicts hold.

- Overstated is the main error: a one-off said as lasting ("always wants burger" from casual
  hyperbole, "wants to know whether their body can look feminine" from one question, "repeatedly"
  from twice), and once the companion's own wording recorded as the user's ("exhausting" when they
  said "it's a lot").
- Duplicates were not found, so merging is not needed yet. The card shows about 15 beliefs a turn,
  ranked, so the count does not hurt replies yet either.
- Trivial: one-off meals, and passing companion remarks stored as its views.

So a second look pays off before consolidation does.

## Design sketch

1. **Second look.** A judge re-reads a belief with more context than the extractor had (the
   messages around the quote and what was said later) and answers keep, correct to X, or wrong.
   Code applies it: a correction is a new belief that supersedes the old one (`superseded_by`
   already exists and is unused), a wrong one is retired, nothing is deleted (ADR 0002), and the
   reason is written by code from the verdict (ADR 0006). Run on new beliefs a day after they are
   recorded, when later messages exist.
2. **Prevention.** The overstated pattern also belongs in the extractor: a one-off is recorded as
   what happened, not as a lasting trait, and only the user's own words count as theirs.
3. **Consolidation, later.** When duplicates or the card's ranking start to matter, merge overlapping
   beliefs into one that supersedes them and carries all their quotes (ADR 0001). Insights ("dives
   into projects when stressed") are inferred and held, never shown freely: the owner has marked
   analysing what something means about them as unwanted.

## Open

- Which model judges. The audit used Sonnet 5.5, which needs reasoning on (OpenRouter refuses it
  off) and cost about $0.003 a belief. A cheaper judge would need its verdicts checked by eye.
- Whether trivial events should age out faster (ADR 0008) instead of being judged.
