"""Does a view the companion holds push against something the user has asked for?

A model compares each candidate view with the user's recorded preferences and boundaries. The
motivating case: the companion's "I want pretend play to be explicit" against the user's own
"wants to pretend and play along". A conflict keeps a view out of the card. A view with no check
yet is not eligible either, so nothing installs itself unchecked.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from companion.core.types import Belief, Json

SYSTEM = """You compare views that a companion holds with things its user has told it they want. \
For each view, say whether it contradicts, or pushes against, any of the user's stated \
preferences or boundaries. For example: a view that the companion will refuse something the user \
said they are happy to do, or insist on something the user said they do not want. A view about \
ideas that has nothing to do with how the two of them interact does not conflict. When unsure, \
say it conflicts. Give your confidence from 0 to 1, and name the user item it conflicts with."""

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "view": {"type": "string"},
                    "conflicts": {"type": "boolean"},
                    "with": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["view", "conflicts", "confidence"],
            },
        }
    },
    "required": ["results"],
}


@dataclass(frozen=True, slots=True)
class Check:
    conflicts: bool
    with_label: str
    confidence: float


def build_prompt(views: Mapping[str, Belief], wants: Mapping[str, Belief]) -> str:
    lines = ["Views the companion holds:", *[f"[{k}] {b.claim}" for k, b in views.items()]]
    lines += [
        "",
        "What the user has said they want:",
        *[f"[{k}] {b.claim}" for k, b in wants.items()],
    ]
    return "\n".join(lines)


def parse(data: Json) -> dict[str, Check]:
    """Label to result. Anything malformed is simply absent, which leaves that view unchecked."""
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        return {}
    out: dict[str, Check] = {}
    for item in cast("list[Json]", data["results"]):
        if not isinstance(item, dict):
            continue
        d = cast("dict[str, Json]", item)
        label, conflicts, conf = d.get("view"), d.get("conflicts"), d.get("confidence")
        if not isinstance(label, str) or not isinstance(conflicts, bool):
            continue
        if isinstance(conf, bool) or not isinstance(conf, int | float):
            continue
        out[label] = Check(conflicts, str(d.get("with") or ""), min(max(float(conf), 0.0), 1.0))
    return out
