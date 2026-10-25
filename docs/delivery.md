# Sending and receiving

How a message comes in over Telegram and how a reply goes out (`src/companion/io/telegram.py`).

## Receiving

Each Telegram update is recorded before its turn runs, so a message is answered at most once, even if
the bot restarts mid-turn. The poll offset moves past a message as soon as it is queued, so stopping
is done with care: on SIGTERM or SIGINT the bot fetches nothing more, answers what it has already
received, the reply in progress included, and only then exits, for up to 30 seconds
(`io/stop.py`). `just restart` waits for that. A hard kill, or a reply still not out
after 30 seconds, can still lose a message that was received but not answered.

A plain message that arrives while the previous one is still being answered, either being written or
held before sending, replaces that answer. The dropped reply is marked undelivered, so the new reply
sees both of their messages. Commands never replace anything.

## Sending

Replies are held for a moment so they land like someone typing, not instantly. `COMPANION_PACE`
chooses how: `off`, `quick`, `natural` (the default) or `slow` (`io/pace.py`). Set `off` when timing
a run by hand. Commands are never held.

A long, plain reply is sometimes sent as two or three messages, the way people text
(`COMPANION_SPLIT`, on unless `off`; `io/split.py`). Cuts fall only at sentence boundaries, and a
reply with quoted speech, as in roleplay, is never split. The ledger and the history keep it as one
reply, so the model never sees the splitting.

On a turn the crisis path reads as urgent with `COMPANION_CRISIS=on`, the turn hands Telegram a
second, fixed message of code's own after the reply (`ThenSend`, ADR 0022): the crisis line. It goes
straight after the reply, and it goes even when the reply could not be delivered. It is stored as the
companion's own message; if it fails to send, it is marked undelivered like a reply.

## What was never seen

A reply the person never received is marked undelivered and left out of what the model reads. The
same applies to part of a reply. When a split reply is cut off after some of its messages went out,
because it was replaced or a send failed, it is marked undelivered, and the part that did arrive is
stored beside it. The model then reads only what was actually seen.
