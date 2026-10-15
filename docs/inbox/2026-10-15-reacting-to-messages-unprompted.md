# Reacting to a message with an emoji, beyond acknowledgements

Added 2026-10-15. Partly built the same day: the first kind below (a reaction alongside a reply) now
exists, behind a small judge, a confidence bar and a cooldown. The rest is still an idea.

## What exists now

The companion reacts with an emoji instead of replying in one situation: when the user's message is
only an acknowledgement or a send-off and a reply would add nothing. A prefilter and a cheap
judge decide that, and a confident judgement cancels the normal reply. The marker reactions used
for flagging and favouriting a turn are separate and are not conversation.

So reactions are currently a way to say less, never a way to say more.

## The idea

People react to messages for many reasons that are not "no reply needed". They react to something
funny, sweet or impressive and also reply. They react to a photo or a long story before they have
time to answer. They react to show they saw it. They sometimes react and say nothing, because
the message was a small share and a reaction is the whole response. A companion that only reacts
to acknowledgements misses most of that.

Possible kinds of reaction:

- **Alongside a reply.** A reaction on the user's message and a normal reply too. A laugh on a joke,
  a heart on something tender.
- **Instead of a reply**, beyond acknowledgements: a small share, a half-joke, a meme.
- **Late.** A reaction that lands after the reply, or some time later, the way people notice a
  message again.
- **On its own message.** Unusual on most platforms, so probably not.

## Things to work out

- **Deciding when.** The existing judge answers "does this need a reply?". This is a different
  question: "would a person react here, and with what?". It could be a second output from the same
  judge call, which keeps it free in latency, or a separate call.
- **Not a pattern.** A reaction on every funny message is as mechanical as none. It needs to be
  occasional and vary, and the same copying problem as repeated openers applies: its own earlier
  reactions become part of what it sees. A reaction on nearly everything stops meaning anything.
- **Which emoji.** The platform allows only a small fixed set. The choice should fit the message
  and the companion's own taste, and avoid always reaching for the same few.
- **What the model sees.** Today a reaction is not in the history. If reactions are part of the
  conversation the model should know what it reacted to, or it will behave as though it said
  nothing. It also affects replay: a reaction is a decision to record with its reason.
- **Mood and relationship.** A reaction means more in a warm moment and can feel dismissive in a
  sad one. Someone who just shared something painful should not get a thumbs-up.
- **Cost.** The reaction itself is free. The judgement is the cost.

## How it could be tested

- Fixtures with a clearly funny, a clearly tender and a clearly flat message, and a judge on
  whether a reaction and its emoji fit. Plus fixtures where a reaction would be wrong (distress).
- Over a replayed conversation, count how often it reacts and how varied the emoji are.
- Flag and favourite data once there is some: moments where a reaction was missed or was off.

## Questions for later

- Is it the same judge that decides reply versus react, or a separate step?
- Should a reaction ever stand in for a reply the user would normally expect?
- How often is right? Probably a measured rate, not a feeling.
