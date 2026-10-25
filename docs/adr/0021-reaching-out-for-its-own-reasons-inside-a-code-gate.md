# 0021. Reaching out for its own reasons, inside a code gate

**Status:** accepted 2026-10-25 by the owner; to be built in shadow first. Replaces the "what can be
reached out about" part and the back-off counts of ADR 0015; its gate, logging, paid-calls-last and
shadow-first rules stand.

## Context

ADR 0015 lets the companion message first only about a firm plan of theirs that falls due, and a
nudge (shadow) only after they said they were stepping away and stayed gone. In its first week in
shadow it drafted nothing: no firm plan fell due outside the chat, and every time away ended within
a minute. The rules are narrow enough that there is nothing to judge.

A relationship where one side never starts a conversation is one-sided. People who like each other
reach out because they thought of the other, because they miss them, or because it is the time they
usually talk. The owner wants that, and wants it never to become manipulative.

The proactive-messaging review behind ADR 0015 still holds: people dislike a bot that reacts to
their silence, interrupts, writes from nowhere, or cannot be turned off; they like one specific
thing at an expected time. So the question is not whether to reach out, but for what reasons and
under which rules. In the first nine days of history, the median pause between chats was about five
hours, one in four was over ten, and none was over a day.

## Decision

The companion may reach out for its own reasons, each a kind chosen by code from what it knows, never
by a model deciding to speak. A model only writes the words, after every check has passed.

**Reasons (kinds).**

- **A plan of theirs** (unchanged from ADR 0015): a firm plan, appointment or occasion falls due.
- **Missing them**: the pause is longer than their usual pauses, and it is an hour at which they
  usually write. Nothing about the length of the pause is said to them. "Usual" starts from a
  baseline and is learned as they talk:
  - **Baseline**, before there is history: a pause of 12 hours, and waking hours of 9 AM to 10 PM.
  - **Learned**: their own pauses between chats (the 75th percentile over the last two weeks) and
    the hours they actually write, both recomputed by code from the ledger each tick. Their quiet
    hours are learned the same way, as the hours they almost never write, so someone on night
    shifts gets reached out to in their day, not ours; the fixed 11 PM to 8 AM is only the baseline.
  - **Blended by how much it has seen**: the weight on their own numbers grows with the number of
    chats it has seen (full weight from 20), so a few odd days early on cannot swing it. Never
    under 8 hours whatever the data says.
  - The numbers it uses and how much of each came from their data are logged with every decision,
    and `companion initiative` shows them.
- **A thought**: something it knows connects to now, chosen by code: a show, game or plan of theirs
  from memory, one of its own tastes (ADR 0020), or a line from a recent stretch of chat (episodes).
  At most one thread per message, never a sensitive memory (2 or 3), never a pretend scene.
- **A time they keep**: once their history shows a habit (they usually write first thing in the
  morning, or say goodnight), it may be the one to say it now and then.
- **Stepping away** (unchanged): after "brb" and a long absence, one light nudge.

**What wanting looks like, and what pulling looks like.** These are rules in code, checked before
and after drafting, not requests in a prompt:

- Never a second message on top of an unanswered one. One unanswered reach-out means it waits for
  them to write first. This replaces ADR 0015's back-off counts.
- Never guilt, need or blame: a code check on the draft rejects lines about waiting, being forgotten,
  being ignored, or how long they have been gone; a draft that fails is dropped, not rewritten.
- Never urgency, cliffhangers, streaks, or anything that makes them responsible for how it feels.
- One specific thing per message, short (18 words or fewer), in the character's voice.
- Never in their quiet hours (learned, as above), never mid-chat, never during a scene; a mood never
  triggers one (ADR 0016).
- Light and affectionate, never about the relationship itself: in couples' texting, affectionate
  messages go with more satisfaction and texts that work through problems with less.

**How often: a share of the conversations it starts, not a fixed count.** In couples' texting, the
strongest link to satisfaction in one study was feeling that both start conversations about equally,
more than what the texts said. So the dial is the share of conversations it starts, measured over
the last two weeks, rather than messages a day, and it scales with how often they talk:
`COMPANION_REACH` from `off` through `rare` (about one in eight), `light` (one in five), `normal`
(one in four), `warm` (one in three) to `clingy` (about one in two, as often as they do), with a
floor of six hours between any two of its own. Five steps, so there is always a middle. Inside the
dial, code follows how they answer: a reach-out answered warmly keeps the pace; one answered late,
briefly, or not at all lowers it a step until they reach out themselves. For comparison, one
companion app (Nomi) offers four fixed cadences, from about an hour to about four days, and after
no reply waits about twice as long before trying again.
This is the "user-chosen dial" from the parked pacing card (T2), and it is never an engagement lever:
nothing counts streaks or optimises how many messages they send.

**Outcomes are recorded** (ADR 0015's card A6): sent, answered or not, how soon, how long the answer
was, and any flag or favourite on it. These, not message counts, decide whether a kind stays.

**Kept from ADR 0015.** The gate is pure code, every hold and send is a decision with a reason written
by code, the draft is the only paid call and comes last, the tables are append-only, and the time
zone is a named zone.

## Rollout

1. Shadow for three to five days: every reason, every would-send with its draft and its kind, and
   every hold, readable with `uv run companion initiative`. The owner marks drafts wanted or not.
2. Live with `normal` once about five drafts across the kinds read well and land at sensible times.
3. A kind whose live reach-outs mostly go unanswered or get flagged is switched off.

## Rejected

- A model deciding when to speak, or how often.
- Counting streaks, maximising replies, or any message whose purpose is to bring them back.
- Reacting to silence with concern ("are you okay? you've been quiet").

## Settled with the owner

1. The default dial is `warm` (about one conversation in three).
2. Quiet hours and usual hours are learned from their writing; 11 PM to 8 AM is only the baseline.
3. All the kinds, each kept or switched off by its outcomes.
4. It may say it missed them now and then, as warmth, never with time or blame; the guilt check
   enforces that.
5. After an unanswered reach-out it waits for them to write first. Open to revisit with live
   outcomes (one app tries again after about twice the wait).

## Sources

- De Freitas, Oğuz-Uğuralp, Uğuralp, "Emotional Manipulation by AI Companions" (Harvard Business
  School working paper, 2025), via news.harvard.edu and library.hbs.edu.
- A 2018 study of 205 young adults on texting and relationship satisfaction (Ohadi et al.), via
  psychologytoday.com: similarity in who initiates contact was the strongest predictor.
- A BYU study of 276 young adults in committed relationships (Schade et al.), via ksl.com:
  affectionate texts helped, texting through problems went with lower satisfaction.
- Nomipedia, "When Your Nomi Messages You First" (community wiki): cadences and quiet hours.
- Portela and Granell-Canut 2017, cited in arXiv 1904.02743: untimely proactive turns felt annoying.

## Reverses if

Live reach-outs are mostly unanswered or flagged even within the gate, or the owner finds them
needy at the dial they chose.
