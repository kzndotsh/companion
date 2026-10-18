# 0013. Every prompt is a versioned file

**Status:** accepted 2026-10-18.

**Decision.** Every piece of text the code sends to a model lives in `src/companion/prompts/` as
`<kind>/<name>/vN.md`: `system/` for whole system prompts (the persona, the judges, the extractors),
`notes/` for lines added to the talker's system block, `messages/` for text sent to the user.
- `manifest.toml` names the live version of each prompt. Shipping a version is one line there.
- A shipped version is never edited. A change is a new `vN.md`, a manifest line and an entry in
  `prompts/CHANGELOG.md` with the reason and, where it was measured, a pointer to `evals/CHANGELOG.md`.
- Dropped and candidate versions stay as files. Nothing is deleted.
- `COMPANION_PROMPT_OVERRIDES` runs another version without shipping it, for evals and trials.
- Placeholders are `$name` (string.Template); a missing value raises rather than sending `$name`.
- A judge's or extractor's logged decision carries `name@version`.
- `tests/test_prompts.py` fails when a file has no changelog entry, an entry has no file, or the
  manifest names a version that does not exist.

**Why.** Prompts were string constants scattered across modules, edited in place. A logged reply
could not be traced to the exact text that produced it, an old version could only be found in git
history, and comparing two versions in an eval meant editing code. As files, every version can be
read, diffed, measured against another and rolled back with one line, and every decision in the log
names the text it came from.

**Consequences.**
- Prompt text is in one visible place, not inside code. Code reads it through `companion.prompts`,
  which only reads packaged text, so `core` may import it (the import layers allow it).
- The history before 2026-10-18 was recovered from git into the files and the changelog.
- Small wording fixes cost a new file and a changelog line. That is the point: a change to what the
  model reads is a change worth recording.

**Reverses if.** The number of versions makes the folder hard to read; then old versions move to an
archive folder, still never deleted.
