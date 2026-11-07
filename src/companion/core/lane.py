"""Which lane a memory sits in (ADR 0026). The scene lane step places each memory; reading which
ones are intimate is a core read (`Store.intimate_lane`), so a feature that must leave them out
does not import the feature that placed them."""

from enum import StrEnum


class Lane(StrEnum):
    EVERYDAY = "everyday"
    INTIMATE = "intimate"
    EXCLUDED = "excluded"
