# Flow

The rhythm of the chat. Each part reads how the conversation is going and shapes the next reply to
fit it. Each part is its own folder, read like a feature, with its own README.

- `topics/`: when a small topic has run its course, one line to move the chat on.
- `length/`: the one word limit a reply gets, chosen by code from their message.
- `questions/`: a note that breaks a run of its own questions, and one that keeps a game of
  questions they set up going.

Each part's note is a `Feature.note`, in its place in `ORDER` (`turn/notes.py`): `length` right
after the scene note, `game` and `topic` near the end, `questions` last. A move on or a game asks them
something (`Offer(asks=True)`), so the question-run note stays out that turn.

The folder was gathered from `features/topics`, `core/turn/length.py`, `core/turn/questions.py`
and `core/turn/game.py` (kzndotsh/companion#1). Stored names did not change: the `length` and
`topic: run its course, moving on` decision keys, the `topics` judge and every prompt file.
