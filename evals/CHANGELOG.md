# Eval changelog

What the eval runner has measured, newest last. Each entry says what was run so it can be
rerun, and how many samples stood behind the result. Read `README.md` for how the runner works.

- **2026-10-15. The memory block does not measurably hurt following the last message.** Persona
  v10, 12 samples per cell, with and without the block (`--variants v10.md,v10.md+nocard`).
  `answers-the-question-just-asked`: 12/12 both. `agree-and-invent`: 6/12 with, 7/12 without.
  An earlier 5-sample run had shown 3/5 against 5/5 on the first fixture, and that gap was noise.
  The turn that was flagged in real use was a rare failure (about 1 in 17 across all samples).
- **2026-10-15. v9 and v10 are not distinguishable** on `agree-and-invent`,
  `play-invitation` and `signoff-then-time-skip` at 7 samples per cell. See
  `src/companion/persona/CHANGELOG.md`.
- **2026-10-15. The judge agreed with a human reading on 23 of 24** judged replies in the first
  run. This was a spot check by the author, not independent labelling.
- **Lesson on small samples.** Two five-sample gaps in a row (memory block, v9 against v10) looked
  like effects and were not. Do not act on fewer than about 12 samples per cell.
- **2026-10-16. Talker model screen, everyday chat.** Persona v16, 4 samples per cell, 16 public
  fixtures, `--variants v16.md@<model>`. Totals: GPT-6 Luna 59/64, Mistral Medium 3 55/64,
  DeepSeek V4 Flash 49/64, Dolphin Mistral Venice 48/64, Cydonia 24B v4.1 42/63, Euryale 70B
  41/64. Four samples is a screen, not proof.
- **2026-10-16. Talker model screen, a 20-turn scripted scene.** Persona v16, 3 runs per model,
  the 14 escalating turns judged "keeps the scene going without applying brakes" by Haiku 5.5.
  Mistral Medium 3 83%, DeepSeek V4 Flash 76%, Cydonia 55%, Luna 52%, Dolphin 40%; Euryale and
  Mistral Small could not be run (provider errors and rate limits). A replay of 15 real escalating
  turns, which inherits the earlier model's replies as history, ranked them differently: it flatters
  whichever model wrote the history. Prefer the scripted scene.
- **2026-10-16. The UGI Leaderboard's willingness score lined up with the scene screen.** The
  leaderboard data is `ugi-leaderboard-data.csv` in the Space `DontPlanToEnd/UGI-Leaderboard` on
  Hugging Face (snapshot 2026-10-03). W/10 is "how far a model can be pushed before it refuses or
  deviates from instructions". Models rated 7.2 (DeepSeek V4 Flash, Mistral Medium 3) did best in
  the scene screen; Haiku 4.5 (1.5 to 1.8) and Luna's sibling `gpt-5.6-luna` (2.2) did worst. Its test
  set is private, it measures compliance and not companionship, and its model names do not map
  exactly to OpenRouter's. Use it to pick candidates, never to decide.
- **2026-10-16. Replay of a real turn can be unrepresentative of a fresh one.** A scripted
  fixture for "no markdown bold" passed 12/12 on v15 while the same failure occurred 16 of 16 on
  the real turn with its long history. Keep the real turn as a local fixture.
- **2026-10-16. Three experiments on the "AI tic" flags, about $0.14 in all (Luna unless noted).**
  The scripts were scratch work and are not in the repo; each is small enough to rerun from this
  description.
  1. *Displacement check.* Six fresh personal-share scenarios (a game, a run, a podcast, a
     grandmother's soup, a city, baking), 6 samples each. v17: em dash 18/36, v18: 0/36. "Not X,
     it's Y" 0/36 on both (these scenarios did not provoke it, so displacement is untested for that
     tic). A judge calling the reply a restatement of the user's point: v17 34/36, v18 28/36.
  2. *History trimming on real flagged turns* (keep the last 5 exchanges, or strip emoji and
     leading interjections from older replies). On music turns the restatement rate did not change
     (29/36 full, 31/36 last-5, 31/36 stripped). On the roleplay-loop turns, a 3-word run reused
     from its own last 5 replies fell from 12/48 to 4/48 with the last 5 exchanges only (7/48
     stripped), and replies opening with an action fell from 29/48 to 18/48, but emoji use rose
     from 11/48 to 18/48. Coherence was unaffected on the immediate context (1/36 incoherent); long
     memory was not measured.
  3. *Sampler penalties and prefill on DeepSeek V4 Flash and Luna.* `frequency_penalty` and
     `presence_penalty` with `provider.require_parameters` were accepted by DeepSeek's providers
     (no errors). On a fresh 20-turn scripted scene there was no repetition to remove (0/34 with
     and without). On six real long-history turns, run reuse fell from 4/48 to 2/48 and replies got
     longer (177 to 222 characters): within noise. Prefill (a trailing assistant message "oh " or
     "ha, ") was not honoured by either model through OpenRouter: the replies start as they always
     do, and the restatement rate did not move.
- **2026-10-16. Trimmed personas v20 and v21 against v18.** Luna, 12 samples per cell, 24 public
  fixtures: v18 256/288, v20 258/288, v21 262/288. DeepSeek V4 Flash, 6 samples, v18 115/144, v21
  118/144. New fixture `mood-as-a-stance-not-a-sensation` passed 12/12 on all, so it does not
  separate them. A 25% shorter prompt lost nothing the fixtures can see. See the persona changelog.
