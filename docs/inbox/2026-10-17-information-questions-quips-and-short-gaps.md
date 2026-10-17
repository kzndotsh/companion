# Four small quality problems seen in one long everyday chat

Added 2026-10-17. Nothing is decided. This is parked, not started.

Four flags from one stretch of ordinary chat (hair care, a shower, dinner) pointed at problems that
share a cause: the companion drifts toward a polished, tidy, "helpful" register whenever the
conversation is easy to wrap up. None of them crashed anything. All four are about whether the
replies sound like a friend texting.

## 1. Information questions turn into assistant answers

When the user asks a practical question (how often to wash long hair, what simple skin and hair
tips to know), the replies change register: capitalised sentences, 350 to 390 characters, em
dashes, a "check with a clinician if you notice thinning" line, and once a bold bullet list. The
persona asks for one or two plain sentences and says no markdown, but it was written for
conversation, and a direct question seems to switch the model into answer mode.

A replay of four such turns (8 samples each, GPT-6 Luna, persona v18 against v21) gave no markdown
on either, so the bullet list was rare. Both ran long and used em dashes (5 of 32 on v18, 9 of 32
on v21), and mentioned a clinician (3 against 8 of 32). The direction suggests the persona trim may
have cost a little, but 32 samples cannot say.

Possible work:
- Public fixtures for information questions: a short plain answer is the pass, and the checks are no
  markdown, no em dash, a word limit, and no boilerplate referral unless the question is medical.
- A persona section for when they ask for information: answer like a friend who happens to know,
  briefly, in plain text, and ask what they need if the question is broad.
- Compare v21 with a candidate on those fixtures before changing the live persona.

## 2. Every thread gets a tidy, soothing ending

Replies tend to close with a reassurance that nothing needs doing now: "the mystery scent can
reveal itself later", "your ends are about to get a much gentler life", "totally normal". The user
noticed that people do not usually write like this. It is the same family as the habit of restating
the user's point, and it is what makes replies feel finished.

Possible work: a fixture where the user mentions a small unresolved thing, with a judge for "does
the reply close it with a reassuring bow"; and check whether the habit check can name it, since it
is a move and not a phrase.

## 3. Forced quips

Replies reach for a joke built from the topic: "the hot water isn't plotting against you", "dinner
roulette", "side quest" twice in one chat. The user called it cheesy, and an earlier flag said the
companion tries to be witty out of the talking points it sees. This is already tracked as the
restating and cleverness habit (see KANBAN T10); this chat adds more examples, all from ordinary
small talk and not from emotional moments.

## 4. It cannot see short gaps

The clock line states a gap only from one minute up. The user wrote "Nom nom" less than a minute
after saying they might get a burger, and the reply asked "burger secured?" as if time had passed.
With no gap line the model has nothing to tell it that almost no time went by.

Possible work: state gaps under a minute in seconds ("Their last message came 40 seconds ago"),
perhaps from 20 seconds up, and add a fixture where a sub-minute reply must not be treated as a
finished action. Check it does not make every reply comment on timing.

## What ties them together

All four show a model that is more fluent than the persona asks it to be. Prompt rules have fixed
the mechanical tics (em dashes, "not X, it's Y") but not the register. The restating habit is
measured across six models and did not move with a rule or examples. The remaining levers are a
different model, trimming what it sees, or naming the move in the habit check.

## Related

- KANBAN T10 (restating) and T12 (shorter history window), both open.
- The greenfield design's texture requirement: brevity, uneven punctuation and lowercase are cues
  people use to tell a person from a model.
- `evals/CHANGELOG.md` for the measured results behind each of these.
