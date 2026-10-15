"""The byte-stable prefix.

Provider prompt caches key on exact bytes, in the order tools, system, messages. Anything that
varies per turn belongs in the user message, never here. A prefix that changes by one byte costs
a full cache miss, so the canonical form is fixed: NFC, LF endings, no trailing spaces, sorted
tool order, sorted JSON keys.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.types import Json

MIN_PREFIX_TOKENS = 1024
CHARS_PER_TOKEN = 4


class PrefixTooShortError(ValueError):
    """Below the smallest cacheable prefix. Write more persona; do not pad with filler."""


@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    description: str
    schema: dict[str, Json]


@dataclass(frozen=True, slots=True)
class Prefix:
    system: str
    tools_json: str
    sha256: str
    estimated_tokens: int


def estimate_tokens(text: str) -> int:
    """A deliberately rough count. The real tokenizer is a provider concern."""
    return len(text) // CHARS_PER_TOKEN


def canonical_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    return "\n".join(lines).strip("\n") + "\n"


def canonical_tools(tools: Sequence[Tool]) -> str:
    ordered = sorted(tools, key=lambda t: t.name)
    payload: list[Json] = [
        {
            "name": t.name,
            "description": canonical_text(t.description).rstrip("\n"),
            "schema": t.schema,
        }
        for t in ordered
    ]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_prefix(
    persona: str, tools: Sequence[Tool] = (), *, min_tokens: int = MIN_PREFIX_TOKENS
) -> Prefix:
    system = canonical_text(persona)
    tools_json = canonical_tools(tools)
    tokens = estimate_tokens(system) + estimate_tokens(tools_json)
    if tokens < min_tokens:
        msg = f"prefix is about {tokens} tokens; the smallest cacheable prefix is {min_tokens}"
        raise PrefixTooShortError(msg)
    digest = hashlib.sha256(f"{tools_json}\n\x00\n{system}".encode()).hexdigest()
    return Prefix(system=system, tools_json=tools_json, sha256=digest, estimated_tokens=tokens)
