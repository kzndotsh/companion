# 0007. Evals replay recorded turns, with a small runner of our own

**Status:** accepted 2026-10-15. Settles the open question of Inspect, Harbor or our own runner.

## Decision

Evals are replays. A fixture holds a turn, a variant swaps one thing (the persona, the model, the
memory block), and each reply is scored by deterministic checks or by a versioned judge. The runner
is a small package, `src/companion/evals/` (about 700 lines in all), run with `uv run companion
eval`. Its rules:

- A spend cap is mandatory, enforced on the real cost each response reports, and the table says
  when the cap stopped a run.
- A judge answers pass, fail or unclear. Unclear is unscored, never a failure. The judge's prompt
  and schema are hashed into every result.
- A sample passes only if every check passes. Every reply and verdict is saved locally.
- Fixtures never hold real conversation text. A fixture is either a short invented script (public,
  in `evals/fixtures/`, runnable by anyone) or an opaque turn id with a generic description
  (private, in `evals/local/`, needs the local database).

Details of fixtures, variants and checks live in `evals/README.md`.

## Why not Inspect or Harbor

The audit of 20 harnesses (`docs/research/2026-10-15_eval-harness-audit`, local only) found the
right shapes: task, trial, verifier, numeric reward, judge as data, results with hashes.

- Our need is one prompt, one reply and a semantic check, with nothing to sandbox and no tool use.
- Harbor's value is containers, cloud sandboxes and benchmark adapters. Inspect's is a mature
  solver and scorer protocol. Both are heavy for a check that takes a second and a third of a cent.
- The audit lists a one-coroutine runner as the shape to avoid. We borrow their splits and keep the
  code small.

## Consequences

- Every persona or prompt change can be measured in one command. Before this, each took a one-off
  script and a guess at the cost.
- The judge is a model. On the first run it agreed with a human reading on 23 of 24 judged
  replies, which is a spot check and not a calibration. A labelled set and an agreement gate are
  still to do.
- Small samples are noisy. Three samples per cell cannot separate two close variants. The project
  rule is about 12 per cell before acting, and 30 on a signal that matters (AGENTS.md).
- The runner measures the talker alone. Decisions made elsewhere in the live loop, such as
  reacting instead of replying, are not exercised by these fixtures.
- Since 2026-10-19: the original fixtures named recorded turns only. Public scripted fixtures
  were added so the set can be shared, and an `epitome` check (reaction, interpretation,
  exploration, support) joined the pass, fail and unclear judge.

## Reverses if

We need to report on public memory benchmarks (LoCoMo, LongMemEval) or compare other products'
agents side by side. Harbor's adapters would then be the maintained way, and its trial shapes
already match ours. The same applies if the companion starts acting in an environment.
