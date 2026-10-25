# Reactions and the other inputs the bot never hears (shelved)

**Status (2026-10-25):** not built; shelved by the owner 2026-10-23, card J24.

From J24 ("inform without waking"), researched and measured 2026-10-23. Shelved by the owner; kept
here so the work is not redone.

## What the bot hears today

Plain text messages only. Commands never start a reply. Everything else is dropped unseen and never
stored: reactions to its messages (Telegram sends them only when the bot asks for `message_reaction`
in `allowed_updates`, and ours does not), stickers, photos, GIFs, voice notes, and edits (J31). So
nothing can wake it by accident yet, and J24's rule (each input wakes, informs or is dropped) only
matters once more is let in.

## Reactions

- **Measured:** a note stating only the fact, "They reacted 😂 to your last message" (or ❤️), on 4
  recorded joke turns, 12 draws each: never mentioned (0/96), the joke not brought back more often,
  tone and length unchanged (`evals/CHANGELOG.md`, 2026-10-23). A bare fact is read and left alone, so
  telling the talker earns nothing; the value would be offline.
- **Others:** Replika offers Love, Funny, Meaningless and Offensive beside thumbs and says they teach
  the companion; its users doubt how much. Nothing published on what Nomi or Character.AI do with ratings.
- **Warnings:** a thumbs-up reward made GPT-4o sycophantic and was rolled back (April 2025); a 2026
  paper on a production character bot found thumbs-ups cluster at the end of chats, often after
  flattery, and favour long answers, so it measured with them but would not optimise on them;
  engagement signals ("kept chatting") mislead more.
- **If ever built:** ask for reactions and record them append-only, never answered and never mentioned;
  map emoji to a few meanings in code (love, funny, meh, off; 👍 is only "seen"); read them in the
  reviews beside `/flag` and `/fav` and to check one judge at a time (jokes laughed at that the quip
  check would redraw), never as a total to raise. Expect them to cluster on sweet end-of-chat replies.
- **Unknown:** whether Telegram sends reactions from a private chat with a bot. One integration doc says
  yes without admin rights; the official docs do not say. Test: turn it on, react once.

## Stickers and photos

The owner would send both. Today both get silence. A sticker carries an emoji, so it could be read as
"[sticker 😂]" and answered like a message; a photo could at least get an honest "I can't see photos
yet", and real image reading needs a check that the everyday model supports it, and a measurement.

## Sources

- https://help.replika.com/hc/en-us/articles/115001095972-How-do-I-teach-my-Replika
- https://help.replika.com/hc/en-us/articles/360000980172-Why-does-Replika-ask-for-feedback
- https://docs.python-telegram-bot.org/telegram.update.html
- https://agpt.co/docs/integrations/block-integrations/triggers-4
- https://arxiv.org/pdf/2603.01973 (CharacterFlywheel)
- https://arxiv.org/pdf/2307.14117v1 (implicit feedback in conversational bots)
- https://arxiv.org/pdf/2602.01002 (preference training and sycophancy)
- https://neuro-api.readthedocs.io/en/stable/command.html (silent context)
