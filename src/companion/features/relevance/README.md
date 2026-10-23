# Relevance

| File | What |
|---|---|
| `logic.py` | pure: its rules, prompts' parsing and notes |
| `run.py` | effects: its `Feature` and what it does with the store and models |

Its prompts stay in `src/companion/prompts/`.

## How it works

Which memories bear on the moment is looked up before the reply (ADR 0018,
`features/relevance/logic.py`, `COMPANION_RELEVANCE` on by default): their message (with its last
reply) is embedded, and only when the closest memory they may see scores 0.42 or more does a small
model pick up to three; at most two picks not already on the card reach the talker in
`notes/relevant`. Outside scenes, 3 s limit. `shadow` runs it beside the turn and only logs it;
`off` stops it.
