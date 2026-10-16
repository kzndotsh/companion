# Looking up older messages when the user asks it to remember

Added 2026-10-16. Nothing is decided. This is an idea to look at later, not a task.

## What happens now

The companion sees two things: the most recent messages (a fixed window of about forty) and a
short memory block built from beliefs the memory step has extracted. Anything older than the
window that never became a belief is invisible to it. When the user says "remember earlier when…",
it can only answer if the thing is still inside the window or happened to be extracted.

So a long relationship will hit this constantly. The companion will seem to forget things that
were said, in full, a few days ago, because only a summary-shaped belief survives and many things
do not make it into one.

## The idea

When the user refers back to something ("remember when…", "what did I say about…", "that thing
from last week"), search the full ledger for the relevant older messages and give the best few to
the model for that turn, the way a person would think back to it.

Possible shapes:

- **Cue-triggered search.** A cheap check for a recall cue in the user's message (remember,
  earlier, last time, you said, I told you). When it fires, run a search and add the results to the
  system block. No cue, no search, so ordinary turns cost nothing extra.
- **A tool the model can call.** Give the model a "look back" tool and let it decide when to use
  it. More flexible. It adds a round trip and the model must be good at deciding, and the talker
  currently has no tools at all by design, for speed.
- **Always-on retrieval.** Search on every turn and add the top matches. Simple and robust, but
  costs a search per turn and risks surfacing old things unprompted, which can feel like recitation.

## Things to work out

- **What to search.** The ledger holds every utterance, both sides. Search by keywords, by
  meaning (embeddings), or both. Keywords are cheap and exact. Meaning catches "that job thing"
  when the words differ.
- **How results reach the model.** The memory card is a system block, not part of the user's
  message, after a finding that the model reads anything in the user's message as something the
  user said. Retrieved messages belong in the system block too, clearly labelled as older
  conversation, with how long ago.
- **Not reciting.** The same restraint as the memory card: use it where it bears on what they
  said, do not read it out. Held-back or sensitive items stay held unless the user raised them.
- **Frames.** Messages from a play scene, a story or a hypothetical must not come back as if they
  were real events.
- **Decisions and replay.** What was searched, what was returned and why would be logged as a
  decision, and the request that was sent must remain exactly rebuildable.
- **Where it falls short.** If the user remembers something the search cannot find, the companion
  should say it does not remember, not invent it. This is the same rule as for any gap in memory.

## How it could be tested

- A fixture where a fact is stated early in a long scripted history, pushed past the window, and
  later asked about with a recall cue. Pass if the answer is right, fail if it is invented or
  "I don't remember".
- A fixture where nothing in the history matches, and the right answer is that it does not
  remember.
- A check that retrieved play-scene messages are not presented as real events.
- A cost check: how many turns trigger a search, and the added latency when they do.

## Questions for later

- Is a cue-triggered search enough, or does it need to be model-chosen?
- Embeddings or keywords first?
- Does this replace some of what the memory step extracts, or sit beside it?
