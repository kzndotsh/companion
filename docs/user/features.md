# Features

Everything the companion does, in one place, in plain words. How each one works is in its README under
`src/companion/features/<name>/` or in `docs/dev/` (the **More** column).

**Status** is the default: **live** changes the chat, **shadow** only works out and logs what it would
do (see `uv run companion shadows`), **your choice** is off until you turn it on in `.env`, **tool** runs only when you run
a command. The settings that turn each one on or off are listed in `README.md`.

## Reading you

| Feature | What it does | Status | More |
|---|---|---|---|
| Knows pretend from real | Tells when a message is play, a story or a what-if, so pretend never becomes a fact about you | live | `docs/dev/turn.md` |
| Backs off when you do | It backs off when you brush it off, even lightly, but can tell that apart from playing shy in a scene | live | `docs/dev/turn.md` |
| Knows the time | Knows the weekday, date and time, and how long it has been since you wrote | live | `docs/dev/turn.md` |
| Notices pauses | Sees where long gaps fell in the chat, so it reads timing right | live | `docs/dev/turn.md` |
| Knows which message you mean | When you reply to a specific message, it sees which one | live | `docs/dev/turn.md` |
| Listens | Works out how serious a message is, so a vent gets heard instead of fixed | live | `docs/dev/turn.md` |
| Small vents | A small complaint gets a short, natural reaction, not a speech | live | `README.md` |
| Cools down when you're rude | A rude message gets a cooler reply that turn | live | `docs/dev/turn.md` |
| Owns its mistakes | When you say it got you wrong, it owns it in a line instead of making something up | live | `docs/dev/turn.md` |
| Stops apologising | After it has owned a slip, it doesn't keep saying sorry | live | `docs/dev/turn.md` |
| Checks in after a hard talk | Coming back hours after a heavy conversation, it gently asks how you are now, once | live | `docs/dev/turn.md` |
| Lets you go | When you say goodbye or goodnight, nothing it says tries to keep you | live | `docs/dev/turn.md` |

## How it replies

| Feature | What it does | Status | More |
|---|---|---|---|
| Right length | Keeps replies to a short message short, instead of three times longer | live | `docs/dev/turn.md` |
| Just a reaction | A short "ok" after something it said can get an emoji reaction instead of a reply | live | `docs/dev/turn.md` |
| Reacts and replies | Now and then reacts to a message with a fitting emoji as well as answering it | live | `docs/dev/turn.md` |
| Mood | Has a mood (cozy, tender, playful) that lasts across hours and shows in how it writes, never stated | live | `features/mood` |
| Breaks its habits | Notices openers and phrases it keeps repeating, and stops copying your emoji back | live | `features/moves` |
| Moves on | When a small topic has run its course, it moves the chat along | live | `features/topics` |
| Plays along with a guess | "You know what time it is?" gets a playful guess from what it knows about you | live | `features/curiosity/guess` |
| Doesn't interview you | After three replies in a row that asked a question, the next one asks none | live | `docs/dev/turn.md` |
| Question game | When you say "ask me anything", it keeps asking | live | `docs/dev/turn.md` |
| Its own emoticons | Uses emoticons and kaomoji of its own now and then, not only yours | live | `features/marks` |
| Quality checks | Catches em dashes, unasked AI disclaimers, stock phrases, tacked-on jokes and empty praise, and writes the reply again. It never edits a reply | live | `docs/dev/turn.md` |
| Feels typed | Waits a little before sending, like someone typing | live | `docs/dev/delivery.md` |
| Several messages | Sometimes sends a long reply as two or three messages | live | `docs/dev/delivery.md` |

## Behind the scenes

| Feature | What it does | Status | More |
|---|---|---|---|
| Two talkers | The everyday talker writes normal replies, and the roleplay talker answers pretend scenes | live | `docs/dev/turn.md` |
| Intimate talk | Lets intimate talk go to the roleplay talker once you have been explicit, never below an age floor | your choice | ADR 0017 |
| Character | Puts a private character sheet over the default personality | your choice | `README.md` |
| Standby talker | If the talker errors or hasn't answered in 10 s, a standby model is asked too and the first answer goes out | live | `docs/dev/turn.md` |
| Telegram or Discord | Runs on one or the other, with the same memory either way | live | `docs/dev/delivery.md` |
| Never loses a message | On a restart it finishes what you already sent and answers each message once | live | `docs/dev/delivery.md` |

## What it remembers

| Feature | What it does | Status | More |
|---|---|---|---|
| Memories with proof | After the chat goes quiet, it saves what it learned, each with your exact words, who said it and whether it was real | live | `docs/dev/memory.md` |
| What it keeps in mind | Shows it about 15 memories each turn, private ones only when the talk is serious | live | `docs/dev/memory.md` |
| Memories that fit the moment | Puts the memories closest to what you're talking about first | live | `features/focus` |
| Finds the right memory | Searches all its memories for ones that bear on what you just said | live | `features/relevance` |
| "Do you remember?" | When you ask it to remember or say it forgot, it searches everything you've told it | live | `docs/dev/turn.md` |
| Times together | Remembers what you two did, for "last night" or coming back after a while | live | `features/episodes` |
| Intimate memories apart | Keeps intimate memories separate: the roleplay talker sees them, everyday chat never does | live | `features/intimate` |
| Where it came from | Keeps a short note with each memory on what you were talking about | live | `features/upkeep/context` |
| Sorting | Tells facts about your life apart from comments about the bot and one-day moments, which fade | live | `features/upkeep/sort` |
| Tidying | Rereads week-old memories each night and checks each new one against what it already knows | live | `features/upkeep/reread` |
| Asks before replacing | When a new memory may contradict an old one, it keeps both and leaves the choice to you in `companion memory review` | live | `features/upkeep/reread` |
| Merging | Suggests joining memories that say the same thing, in `companion memory review`; nothing merges without you | live | `features/upkeep/merging` |
| Backups | Saves a checked copy of everything at each start and once a day | live | `docs/dev/memory.md` |

## Getting to know you

| Feature | What it does | Status | More |
|---|---|---|---|
| Your name and pronouns | Asks what to call you and your pronouns until it knows, then remembers | live | `features/curiosity/basics` |
| Fills the gaps | Sees which part of your life it knows least about and asks one light question | live | `features/curiosity/map` |

## Bringing things up first

| Feature | What it does | Status | More |
|---|---|---|---|
| One thing a day | Brings up at most one thing a day on its own, the most important first | live | `docs/dev/turn.md` |
| Follows up on plans | Remembers your plans and asks how one went next time you write | live | `features/threads` |
| Special days | Notices birthdays, holidays, days coming up and your anniversaries together | live | `features/calendar` |
| Reminders | Reminds you, checks in or says good morning when you ask, once or every day | live | `features/reminders` |
| What's coming | Remembers "dinner's almost ready" until it happens, so it doesn't jump ahead | shadow | `features/now` |
| Writes first about a plan | Messages you first when a plan of yours is due | shadow | `features/threads` |
| Writes first for its own reasons | Messages you first because something reminded it of you, it's your usual time, or it missed you | shadow | `features/reach` |
| Teases when you're gone long | One light tease when you said you'd be quick and were gone much longer | shadow | `features/nudges` |
| Learns your pace | Learns how often to bring things up from how you reacted before | shadow | ADR 0023 |

## Who it is

| Feature | What it does | Status | More |
|---|---|---|---|
| Its own views | Remembers what it has said it thinks, and only settled views shape later replies | live | `README.md` |
| Its own tastes | Keeps its favourites the same from day to day instead of inventing new ones | live | `features/lore` |
| Its own past | Remembers stories about its past it told you, so it tells the same past every time | shadow | `features/history` |
| Keeps its promises | Remembers promises it made, like dropping a word you dislike, and checks it keeps them | shadow | `features/promises` |

## Safety

| Feature | What it does | Status | More |
|---|---|---|---|
| Crisis care | Notices a message that may mean real danger, steps out of any scene, and sends a crisis line when it's urgent. A joke stays a joke | live | `features/crisis` |
| Age floor | Never goes intimate when anything suggests someone under 18. Built into code, no setting changes it | live | `docs/dev/turn.md` |
| Daily spend limit | Stops for the day when model costs hit the cap, and tells you once | live | `docs/dev/turn.md` |

## Your tools

| Feature | What it does | Status | More |
|---|---|---|---|
| `/flag` and `/fav` | Mark a reply that felt off, or one you loved; these decide what gets fixed next | live | `README.md` |
| `/mode` | Tells you which model wrote the last reply and why | live | `docs/dev/turn.md` |
| Why it did that | Every choice it makes is logged with a reason | live | `README.md` |
| Memory tools | See what it believes, answer its questions, merge, retire or restore memories | tool | `README.md` |
| Spending | Shows what the models cost, by purpose | tool | `README.md` |
| Callbacks check | Scores whether replies brought up old memories on their own, and whether it fit | tool | `features/audits/callbacks` |
| Made-up facts check | Measures how often a reply says something about you that it has no reason to know | tool | `features/audits/invented` |
| Replay | Rebuilds any past reply and shows exactly what the model saw | tool | `docs/dev/evals.md` |
| Tests | Tries new prompts and models on saved chats, with fair judges and a spend cap | tool | `docs/dev/evals.md` |
