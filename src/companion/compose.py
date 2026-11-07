"""The one place the bot is put together from `Settings`: the judges' and the memory pass's model,
the talkers, the embedder, where spend is written, and the `Runtime` every turn runs with. The bot
(`daemon`), the one-off commands, the eval commands and the eval samples all build through here, so
they cannot drift apart. Keys and tokens are read here, where a client is made."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypedDict, Unpack

import httpx

from companion.core import switch as sw
from companion.core.clock import utc_now
from companion.core.extractor import StructuredModel
from companion.core.prompt.prefix import Prefix
from companion.core.spend import MeteredEmbedder, MeteredExtractor, MeteredTalker, SpendEvent
from companion.core.talker import Talker
from companion.core.types import RelationshipId
from companion.core.vectors import Embedder
from companion.kit.runtime import Runtime
from companion.models import anthropic, embeddings, openrouter
from companion.models.fallback import ByJudge, RefusalFallback, TalkerFallback
from companion.settings import Settings
from companion.store.sqlite.store import Store

ROLEPLAY_MAX_TOKENS = 700  # scene replies run longer; 400 cut some off mid-sentence


def need(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        msg = f"{name} is not set (put it in .env)"
        raise SystemExit(msg)
    return value


def spend_sink(store: Store, rel: RelationshipId) -> Callable[[SpendEvent], None]:
    """Where every paid call reports what it cost: the store's spend log."""

    def sink(event: SpendEvent) -> None:
        store.record_spend(rel, event, utc_now())

    return sink


def extractor(
    client: httpx.AsyncClient, s: Settings, routes: Mapping[str, str] | None = None
) -> StructuredModel:
    """The judges' and the memory pass's model, with a second model for calls the first refuses.
    With `routes` (judge name to model, `COMPANION_JUDGE_ROUTES`), a judge named there reads on its
    own model first and on the shared first model when that one refuses (`ByJudge`)."""
    key = need("OPENROUTER_API_KEY")
    first = openrouter.OpenRouterExtractor(key, client, s.judge_model)
    shared: StructuredModel = (
        first
        if s.judge_standby is None
        else RefusalFallback(first, openrouter.OpenRouterExtractor(key, client, s.judge_standby))
    )
    if not routes:
        return shared
    own = {
        name: RefusalFallback(openrouter.OpenRouterExtractor(key, client, model), first)
        for name, model in routes.items()
    }
    return ByJudge(shared, own)


def _talker(client: httpx.AsyncClient, s: Settings) -> Talker:
    if s.openrouter:
        return openrouter.OpenRouterTalker(need("OPENROUTER_API_KEY"), client, s.everyday_model)
    return anthropic.AnthropicTalker(need("ANTHROPIC_API_KEY"), client, s.everyday_model)


def _roleplay_talker(client: httpx.AsyncClient, s: Settings) -> Talker | None:
    """The model for pretend scenes and, when allowed, intimate talk (ADR 0017). Set
    COMPANION_ROLEPLAY_MODEL to `none` to use the everyday model for those too. Needs OpenRouter."""
    if s.roleplay_model is None:
        return None
    return openrouter.OpenRouterTalker(
        need("OPENROUTER_API_KEY"), client, s.roleplay_model, max_tokens=ROLEPLAY_MAX_TOKENS
    )


def _with_fallback(client: httpx.AsyncClient, talker: Talker, fallback: str | None) -> Talker:
    if fallback is None:
        return talker
    return TalkerFallback(
        talker, openrouter.OpenRouterTalker(need("OPENROUTER_API_KEY"), client, fallback)
    )


@dataclass(frozen=True, slots=True)
class Models:
    """What the bot asks, each reporting what its calls cost to the spend log."""

    talker: Talker
    roleplay: Talker | None
    judge: StructuredModel  # the judges, with their routes
    memory: StructuredModel  # the memory pass and the night's work
    embedder: Embedder | None  # None when relevance, lore and focus are all off


def models(client: httpx.AsyncClient, store: Store, rel: RelationshipId, s: Settings) -> Models:
    """The talkers, extractors and embedder, metered. Each talker has a fallback: the everyday one
    the standby model, the roleplay one the everyday model."""
    sink = spend_sink(store, rel)
    scene = _roleplay_talker(client, s)
    fallback = s.everyday_standby
    talker = _with_fallback(client, _talker(client, s), fallback)
    roleplay = (
        _with_fallback(client, scene, s.everyday_model if fallback else None) if scene else None
    )
    embedder = (
        MeteredEmbedder(
            embeddings.OpenRouterEmbedder(need("OPENROUTER_API_KEY"), client, s.embed_model), sink
        )
        if s.openrouter and (s.on(sw.RELEVANCE) or s.on(sw.LORE) or s.on(sw.FOCUS))
        else None
    )
    return Models(
        MeteredTalker(talker, sink, "talker"),
        MeteredTalker(roleplay, sink, "roleplay talker") if roleplay is not None else None,
        MeteredExtractor(extractor(client, s, s.judge_routes), sink, "judge"),
        MeteredExtractor(extractor(client, s), sink, "memory"),
        embedder,
    )


class Parts(TypedDict, total=False):
    """What a runtime may be given besides the store, the talker and the persona."""

    judge: StructuredModel | None
    roleplay_talker: Talker | None
    roleplay_prefix: Prefix | None
    embedder: Embedder | None
    scene_reminder: str
    serious_message: str


def runtime(
    s: Settings,
    store: Store,
    talker: Talker,
    prefix: Prefix,
    rel: RelationshipId,
    **parts: Unpack[Parts],
) -> Runtime:
    """The runtime a turn runs with: the parts it is given and every switch as `s` has it. The only
    place a `Runtime` is made."""
    return Runtime(
        store=store,
        talker=talker,
        prefix=prefix,
        rel=rel,
        judge=parts.get("judge"),
        roleplay_talker=parts.get("roleplay_talker"),
        roleplay_prefix=parts.get("roleplay_prefix"),
        embedder=parts.get("embedder"),
        embed_model=s.embed_model,
        scene_reminder=parts.get("scene_reminder", ""),
        serious_message=parts.get("serious_message", ""),
        daily_cap_usd=s.daily_cap,
        modes=s.modes(),
    )
