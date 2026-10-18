# Inbox

A place to drop ideas, thoughts and questions before they are anything. Nothing here is a task or
a decision. It gets emptied every so often.

## Adding

Either way works:

- `just inbox "what if it could tell me when it disagrees"` makes a dated file.
- Create `docs/inbox/YYYY-MM-DD-short-name.md` by hand. One idea per file. Any length. Messy is fine.

A good item says what you noticed or wondered, and where it came from if there is a turn, a flag
or a doc. Options and a recommendation are welcome but optional.

## Emptying

Every so often, read each item and give it one of these fates, then delete the file:

| Fate | Where it goes |
|---|---|
| Decide a design question | An ADR in `docs/adr/` |
| Change how it talks | A new persona version and a line in `src/companion/prompts/CHANGELOG.md` |
| A failure worth testing for | A fixture, once the eval harness exists. Until then keep the turn id |
| Work to do | Do it, or write it as a GitHub issue |
| Needs digging into | A report in `docs/research/` |
| Not now, or no | Delete it. Git keeps it |

The commit that empties the inbox says where each item went. `git log -- docs/inbox/` is the record of
what was thought and what happened to it. No separate log file.

## Rules

- Nothing here is acted on until it is triaged. Do not build from an item you have not read.
- Items that mention private conversation content stay in the repo's private history. Do not paste
  secrets, tokens or account details.
- If an item has sat for a month without a fate, it was not important. Delete it.
