# Memory over time

How memory tidies itself, and how the database is kept safe. What each memory is labelled with is in
the feature READMEs under `src/companion/features/` (context, worth, the memory map, names).

- Memory tidies itself only where a judge matched the owner's own review (ADR 0019,
  `core/consolidate.py`): the night's steps run each on its own (`loops/nightly.py`; one failing does
  not skip the rest) and a night missed while the bot was down is made up five minutes after it
  starts. At 04:00 each memory a week old is read three times; a faded passing moment read so three
  times is closed, and out of date or overstated findings become questions for the owner. When the
  memory pass writes a new memory, the nearest existing one (by embedding, at 0.55 or more) is read as
  a pair three times; read as the same, the new quote becomes evidence on the old memory instead; read
  as a conflict (replaces or contradicts) all three times, it is a question for the owner, who keeps
  one or both (J11). Memories about one thing (one moment split into pieces, one interest restated)
  are grouped three times each night for the last two days (`system/memory-group`, `core/merging.py`;
  `companion memory group` for the whole store); each agreed group, with one wording that keeps every
  detail (`system/memory-merge`), is a merge question in `memory review`, and a conflict between two
  pieces of a pending merge is held back. `COMPANION_CONSOLIDATE` is shadow (log only) unless `on` or
  `off`. Nothing is merged automatically. `companion memory review` asks the owner the questions the
  check raised; `companion merge` merges by hand.
- The database and the character sheets are snapshotted at every start (before migrations) and daily
  (`companion/backups.py`, J36), each copy checked; the newest 7 daily and 7 others are kept in
  `data/backups/` (`COMPANION_BACKUP_DIR`). `companion backup --restore FILE` refuses while the bot
  runs, keeps the current database first, and replaces nothing unless the copy passes its check.
