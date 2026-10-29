# Curiosity

Learning about them on purpose. Each part is its own folder, read like a feature, with its own README.

- `basics/`: asks what to call them and their pronouns until it knows, and keeps their answers.
- `map/`: places each memory in a part of their life and asks one light question about the thinnest part.
- `hook/` (shadow): a light question when their words touch a basic it does not know.
- `guess/`: a guess when they invite one, checked against what memory holds.

Only one note asks them something on a turn: each part's offer says when it asks (`Offer(asks=True)`),
and a part offered after one that asks stays out (`asking` in `kit/features.py`, which other notes read
too). Questions asked for another reason stay with that reason: a thread's follow-up, the check-in after a
heavy talk, the scene lane's curious item. How they want to be referred to stays shared
(`core/turn/address.py`).
