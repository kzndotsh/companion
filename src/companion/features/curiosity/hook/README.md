# Hook (J48)

When their own words touch a basic fact about them without giving it ("I'm getting old"), it logs whether it
would ask about it. Asking about what someone just said reads as care, and a question out of the blue reads as
an interview.

**Status:** shadow (review by 2026-11-05, judged on would-asks that read right, at most daily; at the review of 2026-10-29 it had read only three times, so it got a week more). No switch. It
runs beside the turn, after the reply is out. Nothing reaches the talker.

## How it works

On a casual turn only (not serious, not in a scene, not a goodbye), a small model reads their message, with the
companion's last message before it, and says which basic it touches: `work`, `school` (classes, exams,
studies), `home` (who they live with), `place` (where they live), `age` or `birthday`, or `none`. `none` also covers a message that already states the fact, a
serious or upset one, and one inside a pretend scene. The question is read 3 times (`READS`) with a 5 s limit
each. Code acts only if all three agree. A failed, slow or disagreeing read means no pick that turn.

Code then applies the gate, over earlier hook decisions:

- no hook logged in the last 24 hours (`EVERY`),
- this basic offered fewer than 2 times (`MAX_OFFERS`). Both outcomes below count as offered.

If the gate passes, a stricter judge (`system/basics-known`, 5 s) reads the beliefs the recall look-up may use
(stated for real, sensitivity 2 or less) for that topic (`TOPIC`, one per basic) and returns the ones that state
the fact outright. A
failed or slow read ends the turn with nothing logged. Both judges are named `hook` for `COMPANION_JUDGE_ROUTES`.

The result is logged as a policy decision. `hook (shadow): would ask about a basic their words touched` means
memory held nothing. `hook (shadow): memory already holds the basic their words touched` means it did. The
detail has the basic, their message, the memories found, the model and the prompt version. Nothing is ever sent.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the basics (`Basic`), reading which one a message touches, agreement, the gate (`may_ask`, `EVERY`, `MAX_OFFERS`), the memory topics |
| `run.py` | effects: the three reads, the check of memory (`stated`), the logging, the `Feature` (`HOOKS`) |

## Prompts

- `system/basics-hook`: which basic their message touches without giving it, or none. Unreadable means no pick.
- `system/basics-known`: which memories state the basic outright. Unreadable means nothing is logged.

## Commands

None. Its decisions are in the decision log only.

## Measured

- Birthday and school (added 2026-10-24, `system/basics-hook` v2): not measured yet.
- 2026-10-20: replayed over 341 casual messages, one read called small talk a basic too often, three agreeing reads plus the gate and the memory check would have asked in none of six days. The recall look-up was too loose for "is it known" and a strict prompt replaced it (`evals/CHANGELOG.md`).

## Tests

`tests/features/curiosity/hook/`
