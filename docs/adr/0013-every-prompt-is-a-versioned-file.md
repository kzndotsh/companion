# 0013. Every prompt is a versioned file

**Status:** accepted 2026-10-18.

**Context.** Prompts were string constants scattered across modules, edited in place. A logged reply
could not be traced to the exact text that produced it, an old version could only be found in git
history, and comparing two versions in an eval meant editing code.

**Decision.** Every piece of text the code sends to a model lives in `src/companion/prompts/` as
`<kind>/<name>/vN.md`.

- **Kinds.** `system/` for whole system prompts (the persona, the judges, the extractors), `notes/` for
  lines added to the talker's system block, `messages/` for text sent to the user.
- **The manifest names the live version.** `manifest.toml` has one line per prompt. Shipping a version
  is one line there.
- **A shipped version is never edited.** A change is a new `vN.md`, a manifest line and an entry in
  `prompts/CHANGELOG.md` with the reason and, where it was measured, a pointer to `evals/CHANGELOG.md`.
- **Nothing is deleted.** Dropped and candidate versions stay as files.
- **Overrides.** `COMPANION_PROMPT_OVERRIDES` runs another version without shipping it, for evals and
  trials.
- **Placeholders** are `$name` (`string.Template`). A missing value raises rather than sending `$name`.
- **Decisions name their text.** A judge's or extractor's logged decision carries `name@version`.
- **A test holds it.** `tests/test_prompts.py` fails when a file has no changelog entry, an entry has no
  file, or the manifest names a version that does not exist. `tests/test_persona_versions.py` does the
  same for persona versions.

**Why.** As files, every version can be read, diffed, measured against another and rolled back with one
line, and every decision in the log names the text it came from.

**Consequences.**
- Prompt text is in one visible place, not inside code. Code reads it through `companion.prompts`,
  which only reads packaged text, so `core` may import it (the import layers allow it).
- The history before 2026-10-18 was recovered from git into the files and the changelog.
- Small wording fixes cost a new file and a changelog line. That is the point: a change to what the
  model reads is worth recording.
- A code change that alters what the model is sent also goes in `prompts/CHANGELOG.md`.
- Since: the persona is v40 and the prompts folder has about fifty prompts. It is still readable, so
  the archive folder below is not needed yet.

**Rejected.** (added 2026-10-19 from the context above, not recorded at the time) Prompt strings in code with a version constant; editing shipped versions with the history
left to git.

**Reverses if.** The number of versions makes the folder hard to read. Then old versions move to an
archive folder, still never deleted.
