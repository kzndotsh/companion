# 0007. Evals replay recorded turns, with a small runner of our own

**Status:** accepted 2026-10-15. Settles the open question of Inspect, Harbor or our own runner.

**Decision.** Evals are replays: a fixture names a recorded turn, a variant swaps one thing (the
persona, the model, the memory block), and each reply is scored by deterministic checks or by a
versioned judge. The runner is about 400 lines in `src/companion/evals/`, with these rules:

- A spend cap is mandatory, enforced on the real cost each response reports, and the table says when
  the cap stopped a run.
- A judge answers pass, fail or unclear. Unclear is unscored, never a failure. The judge's prompt and
  schema are hashed into every result.
- A sample passes only if every check passes. Every reply and verdict is saved locally.
- Fixtures hold opaque turn ids and generic criteria, never conversation text. The text stays in the
  local ledger, so fixtures need that database to run.

**Why not Inspect or Harbor.** The audit of 20 harnesses (`docs/research/2026-10-15_eval-harness-audit`)
found the right shapes: task, trial, verifier, numeric reward, judge as data, results with hashes. Our
need today is one prompt, one reply and a semantic check, with nothing to sandbox and no tool use.
Harbor's value is containers, cloud sandboxes and benchmark adapters. Inspect's is a mature solver
and scorer protocol. Both are heavy for a check that takes a second and a third of a cent, and the
audit lists a one-coroutine runner as the shape to avoid. We borrow their splits and keep the code
small.

**Consequences.**
- Every persona or prompt change can be measured in one command. Until now each took a one-off
  script and a guess at the cost.
- The judge is a model. On the first run it agreed with a human reading on 23 of 24 judged replies,
  which is a spot check and not a calibration. A labelled set and an agreement gate are still to do.
- Small samples are noisy. Three samples per cell cannot separate two close variants.
- The runner measures the talker alone. Decisions made elsewhere in the live loop, such as reacting
  instead of replying, are not exercised by these fixtures.

**Reverses if.** We need to report on public memory benchmarks (LoCoMo, LongMemEval) or compare other
products' agents side by side. Harbor's adapters would then be the maintained way, and its trial
shapes already match ours. The same applies if the companion starts acting in an environment.
