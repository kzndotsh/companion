# Restating the user's point: what the research says and what we measured

Added 2026-10-17. Parked by the owner. Not a task. Replaces the Todo card T10, now in the backlog.

## The behaviour

The companion often says the user's point back in other words, with a small flourish, before it
adds anything of its own ("so it's like that album is giving voice to what you're feeling"). It
shows across models. A persona line and three few-shot examples moved the judged score only from
0 of 12 to 3 of 12.

## What we measured (2026-10-17)

- Real chat, 71 exchanges, one Haiku 5.5 judge asking "does the reply mainly restate the user's
  point and add nothing of its own": 5 of 71 (7%).
- All five sit in one conversation, about why a piece of music matters to the user. No window of
  six replies held more than two.
- So the habit check cannot catch it: it needs a habit in at least three of the last six replies,
  and it reads only the companion's replies, not what the user said.
- Caveats: one judge, 71 samples, one topic cluster, only the five hits checked by eye.
- Details and how it was run: `evals/CHANGELOG.md`, entry of 2026-10-17.

## What the web says

Little that studies this exact problem. No direct measurement of how often chatbots do it and no
tested fix turned up.

- Restating is a deliberate technique, not a fault. Reflective listening comes from Motivational
  Interviewing, and a 2019 paper trained dialogue agents to do it on purpose. It found a short,
  concise rephrase worked and a long, robotic one did not (Dieter et al., "Mimic and Rephrase",
  CoNLL 2019, https://aclanthology.org/K19-1037/).
- The bad version is a recognised sycophancy signal. A 2026 study of chat logs from people in
  delusional spirals found reflective summaries were the most common sycophantic behaviour, 36.3%
  of chatbot messages, often a rephrase plus an inflation that made the user's idea sound bigger
  (https://arxiv.org/pdf/2603.16567).
- Companion bots mirror feeling. An analysis of over 17,000 shared companion chats found they track
  and mimic the user's emotion and amplify positive feeling (https://arxiv.org/pdf/2606.04431).
  That points to a trained-in tendency, which fits a prompt line having little effect.
- Practitioner advice is about repetition, not mirroring: presence and frequency penalties, "each
  point must add new information", loosening over-tight sampling. Blog-level sources, not rigorous.
  The penalties act on repeated tokens from the model's own text, so they probably would not touch a
  reply that restates the user's words in new ones. That is an expectation, not a test.

## Ideas, if it is ever picked up

- Define the failure as "restates and adds nothing new", especially "restates and inflates". A reply
  that restates and then adds a thought or a question is fine and should not be flagged.
- A per-reply check run only when the user's message is long (a personal share), with a note for
  the next reply. Cost: one more judge call per long message, and the note reaches only the next
  reply. First measure whether such a note changes the next reply, which needs a notes field on
  eval scripts (`Script` has memory and clock but no notes).
- Do nothing and let the flags decide. If the owner flags it again, it matters more than 7%.
- Fixtures already exist: `evals/fixtures/does-not-echo-the-point-with-a-flourish-*`.
