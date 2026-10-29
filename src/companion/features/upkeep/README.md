# Upkeep

Everything done to a memory after it is written, feeding one review queue for the owner
(`companion memory review`). Each part is its own folder, read like a feature, with its own README.

**At write**, after each memory pass:
- `sort/`: whether a new memory is about their life, about the companion, or one day's routine.
- `reread/` (its write-time half): the repeat check, which turns a repeat of an old memory into another
  quote for it and raises a question when a new memory may replace or contradict an older one.
- `context/`: a short line on what was being talked about, shown beside the memory.

**Nightly**, at 04:00 local time (`memory/nightly.py`):
- `reread/`: the re-read of settled memories, which closes faded passing moments and queues questions.
- `merging/`: merge proposals, memories about one thing grouped for the owner to approve.
- `sort/` (its nightly half): retiring routine moments after their week.

The parts may use each other; nothing outside upkeep imports a part except the registry, the memory
side and the store facade, as for any feature.
