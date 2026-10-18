# Free models for evals: the Kiro gateway and OpenRouter free models

Checked 2026-10-18. Use these for cross-model checks and, once calibrated, judging (TODO J44). They are
not a measurement of the live talker. Public fixtures only: real turns and beliefs are not sent to them.

## Kiro gateway

A local proxy, [jwadow/kiro-gateway](https://github.com/jwadow/kiro-gateway), built from the owner's
dotfiles (`packages/kiro-gateway`, `modules/ai/kiro-gateway.nix`), runs as a system service on
`127.0.0.1:9000` and forwards to Kiro (Amazon Q Developer Pro). Free and unlimited in tokens, but keep it
to one call at a time.

- **API:** Anthropic style, `POST /v1/messages` with `x-api-key` set to `PROXY_API_KEY` from
  `~/.secrets/ai.env` (the eval runner also reads `KIRO_GATEWAY_API_KEY`). Also `/v1/models` (a fixed list
  in the gateway, not what the account has), `/v1/messages/count_tokens` and an OpenAI-style
  `/v1/chat/completions`.
- **Use from evals:** `--variants v26.md@kiro/claude-sonnet-4.6` (`src/companion/models/kiro.py`).

### Models on this account

| Model | Hidden input tokens ("say hi") | Takes a short persona |
|---|---|---|
| claude-sonnet-4.6 | about 970 | no: "I can't discuss that. I'm Kiro" |
| claude-sonnet-4.5 | about 4,900 | no: "I be Kiro, not Pip" |
| claude-opus-4.5 | about 4,900 | no |
| claude-haiku-4.5 | about 4,900 | no |
| deepseek-3.2 | about 5,200 | yes |
| minimax-m2.1, minimax-m2.5 | about 4,130 | yes |
| glm-5 | about 4,070 | yes |
| qwen3-coder-next | about 3,260 | yes |

`claude-opus-4.6`, `claude-opus-4.7` and `claude-sonnet-4` are listed but return 400 `INVALID_MODEL_ID`
(not on this account).

The Claude models refuse a short persona, but with the full companion persona, card and notes Sonnet 4.6
stayed in character: no reply of 252 named Kiro (`evals/CHANGELOG.md`, 2026-10-18).

### What the gateway does to a request

- **No system role.** The gateway pastes the system prompt into the first user message
  (`converters_core.py`), so persona, card and notes reach the model as user text (compare ADR 0012).
- **A hidden prompt from Amazon.** Requests carry `origin: AI_EDITOR`; Kiro adds a coding-assistant prompt
  (the table above). It cannot be removed from the gateway.
- **Dropped parameters.** `temperature` and `tool_choice` are accepted and not forwarded: no forced tool
  calls, so a judge must answer in JSON text (some models wrap it in a code fence or add chatter).
- **Fake reasoning, on by default.** The gateway injects thinking tags and a paragraph about them;
  `"thinking": {"type": "disabled"}` per request turns it off (the eval adapter always sends it).
- **Web search.** The gateway adds a `web_search` tool to every request unless `WEB_SEARCH_ENABLED=false`;
  a non-streaming caller can get a tool call back instead of text. Kiro's search API returned 400 for
  this account, so it does not work now.
- **Settings** (in `~/.secrets/ai.env`, shared with the owner's other projects): `WEB_SEARCH_ENABLED`,
  `FAKE_REASONING`, `TRUNCATION_RECOVERY` (another appended paragraph), `DEBUG_MODE` (log full payloads).

## OpenRouter free models

Model ids ending in `:free`. Limits: 20 requests a minute and, since the account has bought more than
$10 of credits, 1,000 a day (`GET /api/v1/key` shows `free_model_daily_requests`). Other accounts or keys
do not raise them. The eval runner calls them one at a time, about three seconds apart.

| Model | Size (active / total) | Status for this account |
|---|---|---|
| dots-studio/dots-3-note-preview | 16B / 280B, 512K context | works |
| xingchen-agi/xing4.0-29b-a4b | 4B / 29B, 262K | works |
| google/gemma-4-31b-it, gemma-4-26b-a4b-it | 31B dense; 3.8B / 25B | often 429 (provider busy) |
| nvidia/nemotron-3-ultra-550b-a55b and the other Nemotrons | up to 55B / 550B | blocked by the privacy guardrail |
| poolside/laguna-s-2.1, liquid/lfm-2.5-2.6b | | blocked by the privacy guardrail |
| thinkingmachines/inkling, inkling-small | | refused: "only available on agentic harnesses" |
| cohere/north-mini-code | | works, a code model |

"Blocked by the privacy guardrail": the only free provider may log or train on prompts, and the account
does not allow that. OpenRouter keeps a separate setting for free models
(openrouter.ai/settings/privacy), so allowing it there would not touch the paid models the bot uses. That
is the owner's call.

## How they compare

The four-model run of 2026-10-18 (`evals/CHANGELOG.md`): on 62 shared fixtures, Kiro Sonnet 4.6 89%, Luna
83%, xing 66%, dots-3 58%. Kiro Sonnet 4.6 is a useful second opinion; the two small free models miss the
subtle behaviours and say little about the companion.
