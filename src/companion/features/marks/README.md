# Marks

Its own emoticons and kaomoji, offered by code now and then, so it has marks of its own instead of only copying theirs. It exists because it used almost no text emoticons on its own, and copied theirs when they sent one.

**Status:** live. Switch: `COMPANION_MARKS` (`on` default, `off`). Runs before the reply, as a note sent after the history on a casual turn. No model call is made.

## How it works

On a casual turn, code decides whether to offer a mark. A casual turn is one the listening judge read as not serious (severity 0), outside a pretend scene, and not a goodbye (`is_casual`). On any other turn, or when listening failed, nothing is offered. A mark is offered when their message has an emoticon, and on about one other turn in four. The draw comes from a hash of the turn id, so a replay draws the same.

Code then picks one mark at random from `marks.txt`, leaving out any mark that stands on its own in their message or in the companion's last six replies (a word mark as a whole word, a symbol mark not glued to other symbols, so ✧ inside a longer kaomoji does not rule ✧ out). The pick also depends only on the turn id. If every mark is ruled out, nothing is offered. The pick goes in one line after the history (`TalkerRequest.tail`), where it weighs most: "If an emoticon fits this reply, use this one of yours". The model may still use none.

Once the turn is stored, the offer is logged as the decision `mark: one of its own offered`, with the mark. It does not touch emoji, which the model already chooses well on its own. When their message has a mark, a different note is sent instead (`notes/own-mark-theirs`): it names their mark as theirs, to leave to them, then offers one of its own. Offering its own alone did not stop it copying theirs; naming theirs mostly does. The marks are kept as text in `marks.txt`, one per line, because they are made of look-alike characters that are easy to damage in code.

**Never.** It never offers a mark on a serious turn, in a scene or on a goodbye, never one they just used, and never rewrites a reply.

## Files

| File | What |
|---|---|
| `logic.py` | pure: when a turn offers a mark, which one (never theirs, never one it used lately), the note text (`EVERY`, `RECENT`, `OFFERED`) |
| `marks.txt` | the marks, one per line (kept as text: they are made of look-alike characters) |
| `run.py` | effects: the note after the history on a casual turn, logged with the mark (`MARKS`) |

## Prompts

- `notes/own-mark`: offers one mark of its own, sent after the history. There is no judge, so there is no failure to read.
- `notes/own-mark-theirs`: the same offer when their message has a mark, naming theirs as theirs.

## Commands

None. An eval sample offers a mark as the turn does, on a casual turn (a fixture with `labels` of
severity 0), drawn afresh each sample.

## Measured

- 2026-10-23: gpt-6-luna, persona v41, 4 copying fixtures and 8 everyday ones. With the note in the system block it used one of its own in 10 of 80 replies. After the history, 66 of 80, with 20 different marks. Copying theirs stayed at about 60% on the copying fixtures either way (`evals/CHANGELOG.md`).
- 2026-10-24: 20 real everyday turns where they used a mark, 2 draws each, gpt-6-luna with the owner's character: it copied theirs in 14 of 40 replies with `notes/own-mark`, 4 of 40 with `notes/own-mark-theirs` (`evals/CHANGELOG.md`).

## Tests

`tests/features/marks/`
