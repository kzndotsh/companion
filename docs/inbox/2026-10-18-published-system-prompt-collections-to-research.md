# Published system prompt collections to research

Added 2026-10-18. Not reviewed yet.

## The links

- https://github.com/asgeirtj/system_prompts_leaks
- https://github.com/elder-plinius/CL4R1T4S
- https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools
- https://github.com/jujumilk3/leaked-system-prompts
- https://github.com/YeeKal/leaked-system-prompts
- https://github.com/EliFuzz/awesome-system-prompts
- https://github.com/exebyt3/prompt-vault

These are collections of system prompts from shipped AI products, gathered from the products or
reconstructed by users. They overlap, and some entries are likely stale, partial or fabricated.

## Why they might help

One published companion config (a voice companion app's full prompt set) already gave two ideas worth
trying: a reply length varied by code each turn (T16) and a relationship stage that swaps one line of the
prompt as closeness grows (T17). It also showed what not to copy: fixed greeting lines, catchphrases, and
rules that contradict each other. Other products' prompts may show how they handle the problems this
project keeps meeting: restating the user's point, therapy-like wording, reply length, characters laid
over a base prompt, memory shown to the model, honesty about being an AI, and safety for distress.

## What to look for

- Companion and character products first (persona, memory, closeness, proactive messages), then
  general assistants for structure (how they mark background, how they order sections, what they ban).
- Rules that are enforced by code or by a separate judge, not only stated in the prompt.
- Any measurement or stated reason behind a rule. Most will have none, so each idea is a hypothesis to
  test with a prompt version and an eval, never a change by itself.
- Patterns to avoid: contradictions, quoted phrases a model would parrot, manipulative engagement rules.

## Notes for whoever reviews it

Read only; do not run anything from these repositories. Whether a prompt is genuine is often unknown, so
say so in the review. Write the review to `docs/research/` and link it here.
