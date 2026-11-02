# Photos they send

Added 2026-11-02.

## What happens now

A photo never reaches the model. On Discord a message with only a picture has no text and is dropped
without a reply or a log line (`io/discord.py`); a picture with words keeps the words, and the model is
not told a picture came with them. On Telegram anything that is not text is skipped (`io/telegram.py`).

In 1,711 messages from 2026-10-15 to 2026-11-02 about 7 mention a picture, a screenshot or "see this",
none clearly about a photo they sent. That says little: sending one has never worked.

## What the models can do

On OpenRouter all three chat models take image input: GPT-6 Luna, DeepSeek V4.1 Flash and Claude Haiku
5.5. The embedding model is text only. Claude counts about (width/28) x (height/28) tokens, capped near
1,600 at a 1,568 px long edge, so roughly a tenth of a cent per photo on Haiku; OpenAI patch models
count by 32 px patches. No per-image price is listed for these models on OpenRouter. Anthropic says
Claude does not name people in photos and does not process explicit images against its policy. Claude
reads only a GIF's first frame. OpenAI lists small, rotated and non-Latin text and counting as weak.

## Outside

- SillyTavern captions an image once (a local captioner or a multimodal model, prompt customisable) and
  attaches the caption to the user's message; later turns read the caption, not the pixels.
- Replika reads photos the user sends (selfies, loved ones) and talks about them; it cannot send photos
  except generated selfies, and says so in its help centre.
- Multimodal memory studies (MemLens, Mem-Gallery) find that captions lose visual detail, and that
  neither long context nor caption memory alone is reliable for remembering images.
- Discord attachment links expire (about a day); a Telegram file link lasts at least an hour, files up
  to 20 MB. Download at receipt, keep the file locally, never store the link.

## Options, smallest first

1. **Stop losing them.** A photo is stored as a marker of its own (they sent a photo, with any words),
   and the talker is told it cannot see it, so it says so plainly instead of guessing. No vision call.
2. **See it on its turn.** The photo, downscaled, goes to whichever talker answers, on that turn only.
   Later turns see the marker. Nothing about the photo enters memory unless their own words say it.
3. **A description kept beside it.** A small model describes the photo once at receipt in plain words
   (who or what, mood, setting, any visible text), stored with the message as a description, never as
   their words. Later turns and replays read it. Memory still needs their quote (ADR 0001, 0010): a
   description can be the frame of a memory, not its quote.
4. **Screenshots apart.** A screenshot of a chat or a page is transcribed, and the words in it are
   someone else's, framed as quoted, never as theirs (`core/quoted.py`).
5. **Intimate photos.** A provider may refuse, the judges on Haiku will. The floor (ADR 0017, 0026)
   decides first; a refused or failed read is logged and the turn goes on with the marker.

Open questions: whether any of this earns its place before photos are actually sent; which talker reads
a photo on a scene turn; whether photos are kept on disk and for how long.
