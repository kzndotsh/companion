"""What a one-off command's job is handed: the store, the judges' model, the relationship and the
HTTP client. The model is metered, so what a command spends counts toward the day's spend. Opened
and closed by `companion/commands.py`."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from companion.core.extractor import StructuredModel
from companion.core.types import RelationshipId
from companion.store.sqlite.store import Store


@dataclass(frozen=True, slots=True)
class Services:
    store: Store
    judge: StructuredModel
    rel: RelationshipId
    client: httpx.AsyncClient  # for what a command builds besides the judges' model
