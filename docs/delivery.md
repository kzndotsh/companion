# Sending and receiving

How a message comes in and how a reply goes out, on Telegram or on Discord. `COMPANION_PLATFORM`
picks one at start: `telegram` (the default) or `discord`. Only one runs at a time. Either way it is
the same companion with the same memory: one relationship, one database, and each message is stored
with the platform it came over (`telegram` or `discord`).

`src/companion/io/delivery.py` holds everything about how a reply goes out, once for both platforms.
Under it, a small `Transport` does the platform's own part: bring in the allowed user's messages, send
one message, react to one, show typing. `io/telegram.py` is Telegram's (long polling, update ids,
the Bot API's calls); `io/discord.py` is Discord's (discord.py, which owns the gateway, heartbeats,
reconnects and Discord's rate limits).

## Receiving

Only text from the one allowed user is taken: on Telegram from `TELEGRAM_USER_ID` in their private
chat with the bot, on Discord from `DISCORD_USER_ID` in a direct message. Anyone else's messages,
group chats, server channels, the bot's own messages and anything that is not text are passed over.

Each message is recorded as handled before its turn runs, so it is answered at most once, even if the
bot restarts mid-turn. The record is the store setting `telegram.last_update_id` (an update id) or
`discord.last_message_id` (a message id). On a start, Telegram resumes polling past the recorded
update. Discord fetches the direct messages that came after the recorded one, oldest first, answers
them, and then takes new ones as they come; a message that shows up both ways is queued once. On a
first start, with nothing recorded, nothing old is answered. When Discord's connection drops and
cannot resume, discord.py starts a new session and the messages sent in the gap never arrive as
events, so on each new session after the first it fetches them the same way.

On SIGTERM or SIGINT the bot takes nothing more, answers what it has already received, the reply in
progress included, and only then exits, for up to 30 seconds (`io/stop.py`). `just restart` waits for
that. A hard kill, or a reply still not out after 30 seconds, can still lose a message that was
received but not answered on Telegram, where the poll offset has already moved past it.

A plain message that arrives while the previous one is still being answered, either being written or
held before sending, replaces that answer, and the new reply sees both of their messages. A reply
that was already written and then dropped is marked undelivered. Commands (`/flag`, `/fav`, `/mode`)
never replace anything. Typed as text they work on both platforms. On Discord they are also the bot's
own slash commands, and a message's Apps menu has Flag this and Favorite this, which mark that
message's turn and ask for an optional note (`io/discord.py`). These answer privately,
only the allowed user can use them, and they are synced to Discord only when they change: its
command endpoint is rate limited, with day-long lockouts reported.

The id of each message that carries part of a reply is kept with its turn (`sent_messages`), and so
is the id of each of their messages, when it is stored (`received_messages`, from 2026-10-27, the
spend cap's turns included). `/flag` or `/fav` sent as a reply to either marks that turn, not the
latest. A reply to a message it has no record of, such as one sent before ids were kept, marks
nothing and says so.

A plain message sent as a reply also brings the message it points at: its text and whether the
companion or they sent it (`Incoming.quoted`). Discord sends it with the message (a forward or a
deleted message brings nothing); Telegram sends it too, or only the part they picked when they
quoted part of it. The turn quotes it in a note (`docs/turn.md`).

## Sending

Replies are held for a moment so they land like someone typing, not instantly. `COMPANION_PACE`
chooses how: `off`, `quick`, `natural` (the default) or `slow` (`io/pace.py`). Set `off` when timing
a run by hand. Commands are never held. The wait is a reading pause and then typing: the typing
indicator stays off until the reading pause is over, as someone who has just seen the message would
not be typing yet, and then stays on while the reply is written and held, refreshed every four
seconds. A reply ready within the pause, such as a reaction, never shows typing.

When Telegram answers "too many requests", a call waits the full time it asks for and tries again,
for up to a minute of waiting in all; asking sooner is refused and can lengthen the block. A reply
still refused after that is marked undelivered. On Discord, discord.py waits out rate limits itself.
discord.py sets no time limit of its own, so a Discord send that gets no answer in 15 seconds, as on a
dropped connection, is tried once more and then marked undelivered. If the first try had gone
through after all, the message shows twice.
On both, the typing indicator never waits: it is skipped.

A long, plain reply is sometimes sent as two or three messages, the way people text
(`COMPANION_SPLIT`, on unless `off`; `io/split.py`). Cuts fall only at sentence boundaries, and a
reply with quoted speech, as in roleplay, is never split. The ledger and the history keep it as one
reply, so the model never sees the splitting. Whatever the split setting, a message is never longer
than the platform takes (4096 characters on Telegram, 2000 on Discord): a longer part is cut after the
last sentence that fits, else at a space, and goes as several messages.

On a turn the crisis path reads as urgent with `COMPANION_CRISIS=on`, the turn hands delivery a
second, fixed message of code's own after the reply (`ThenSend`, ADR 0022): the crisis line. It goes
straight after the reply, and it goes even when the reply could not be delivered. It is stored as the
companion's own message; if it fails to send, it is marked undelivered like a reply.

Reminders go out over the running platform and are stored with its name.

## What was never seen

A reply the person never received is marked undelivered and left out of what the model reads. The
same applies to part of a reply. When a split reply is cut off after some of its messages went out,
because it was replaced or a send failed, it is marked undelivered, and the part that did arrive is
stored beside it. The model then reads only what was actually seen.

## Discord setup

1. In the [Discord Developer Portal](https://discord.com/developers/applications), create an
   application, open **Bot**, and copy its token (reset it if none is shown). No privileged intent
   is needed: the bot asks only for direct messages, whose text Discord sends without the message
   content intent.
2. Make sure it can message you. Either invite it to a server you are in (**OAuth2**, scope `bot`, no
   permissions needed), or install it to your account as a user app (**Installation**, User Install).
   Then open a direct message with it.
3. Find your own user id: in Discord's settings turn on **Advanced > Developer Mode**, then
   right-click your name and choose **Copy User ID**.
4. In `.env`, set `COMPANION_PLATFORM=discord`, `DISCORD_BOT_TOKEN` to the token and
   `DISCORD_USER_ID` to your id. Keep `TELEGRAM_USER_ID`: it names the relationship and its
   database, so the companion remembers the same things. Then `just restart` and check that the
   "up as" line says `platform discord`.

The token is scrubbed from every log like the other secrets, and no error the bot raises carries it.
