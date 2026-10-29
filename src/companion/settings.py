"""What the bot runs with, read from the environment once (`.env`, README's table).

Every switch is one row of a table: its variable, the name on the startup line, the values it takes
and its default. "off", "0", "no" and "false" mean off and "on", "1", "yes" and "true" mean on for
every switch; anything else is the default. The startup line is printed from the same values the
bot is configured with, so the two cannot drift. Keys and tokens are not settings: they are read
where a client is made and never kept here.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from companion.io.pace import DEFAULT_PACE, PACES, pace_factor
from companion.models import anthropic, embeddings, openrouter

ROLEPLAY_MODEL = "deepseek/deepseek-v4.1-flash"
DEFAULT_DAILY_CAP_USD = 10.0
# The crisis risk judge reads on DeepSeek first: Haiku's provider refused many crisis messages
# (judge bake-off, evals/CHANGELOG.md, 2026-10-25). Haiku answers when DeepSeek refuses.
JUDGE_ROUTES = "crisis=deepseek/deepseek-v4.1-flash"

OFF = frozenset({"off", "0", "no", "false"})
ON = frozenset({"on", "1", "yes", "true"})
# Settings that were renamed (vocabulary audit, kzndotsh/companion#1). An old name still set stops
# the bot with the new one, so a stale .env line is never silently read as the default.
RENAMED = {
    "COMPANION_SURFACE": "COMPANION_PLATFORM",
    "COMPANION_MODEL": "COMPANION_EVERYDAY_MODEL",
    "COMPANION_TALKER_FALLBACK": "COMPANION_EVERYDAY_STANDBY",
    "COMPANION_REFLECT_MODEL": "COMPANION_JUDGE_MODEL",
    "COMPANION_FALLBACK_MODEL": "COMPANION_JUDGE_STANDBY",
    "COMPANION_JUDGE_MODELS": "COMPANION_JUDGE_ROUTES",
    "COMPANION_LOOP_NOTES": "COMPANION_HEDGED_PLANS",
    "COMPANION_CONSOLIDATE": "COMPANION_REREAD",
}


@dataclass(frozen=True, slots=True)
class Switch:
    env: str
    label: str  # its name on the startup line
    values: tuple[str, ...]  # the first is the default
    shown: Mapping[str, str] | None = None  # how a value reads on the startup line, when not as is

    def read(self, environ: Mapping[str, str]) -> str:
        raw = environ.get(self.env, "").strip().lower()
        value = "off" if raw in OFF else "on" if raw in ON else raw
        return value if value in self.values else self.values[0]


# In the order they appear on the startup line.
SWITCHES: tuple[Switch, ...] = (
    Switch("COMPANION_PLATFORM", "platform", ("telegram", "discord")),  # which chat it runs on
    Switch("COMPANION_SPLIT", "split", ("on", "off")),
    Switch("COMPANION_LISTEN", "listen", ("on", "off")),
    Switch("COMPANION_INITIATIVE", "initiative", ("shadow", "off")),
    Switch("COMPANION_MOOD", "mood", ("on", "shadow", "off")),
    Switch("COMPANION_RESAMPLE", "resample", ("on", "off")),
    Switch(
        "COMPANION_ROUTE_INTIMATE", "intimate", ("off", "on"), {"on": "may route", "off": "stays"}
    ),
    Switch("COMPANION_RELEVANCE", "relevance", ("on", "shadow", "off")),
    Switch("COMPANION_REREAD", "re-read", ("on", "shadow", "off")),
    Switch("COMPANION_PROMISES", "promises", ("shadow", "off")),
    Switch("COMPANION_LORE", "lore", ("on", "shadow", "off")),
    Switch("COMPANION_REMINDERS", "reminders", ("on", "off")),
    Switch("COMPANION_EPISODES", "episodes", ("on", "shadow", "off")),
    Switch("COMPANION_MARKS", "marks", ("on", "off")),
    Switch("COMPANION_HEDGED_PLANS", "hedged plans", ("loose", "off"), {"off": "strict"}),
    Switch("COMPANION_REACH", "reach", ("warm", "off", "rare", "light", "normal", "clingy")),
    Switch("COMPANION_CRISIS", "crisis", ("shadow", "on", "off")),
    Switch("COMPANION_CALENDAR", "calendar", ("on", "off")),
    Switch("COMPANION_NOW", "now", ("shadow", "on", "off")),
    Switch("COMPANION_HISTORY", "history", ("shadow", "on", "off")),
    Switch("COMPANION_SCENE_MEMORY", "scene", ("shadow", "on", "off")),
)
_BY_LABEL = {s.label: s for s in SWITCHES}


def _daily_cap(raw: str) -> float | None:
    """COMPANION_DAILY_CAP_USD in dollars; unset is the default, "off", "none" or 0 remove it."""
    raw = raw.strip().lower()
    if raw in ("off", "none", "0", "0.0"):
        return None
    try:
        value = float(raw) if raw else DEFAULT_DAILY_CAP_USD
    except ValueError:
        return DEFAULT_DAILY_CAP_USD
    return value if value > 0 else None


def _judge_routes(raw: str) -> Mapping[str, str]:
    """COMPANION_JUDGE_ROUTES, `judge=provider/model` pairs separated by commas; "none" or "off"
    sends every judge to the shared model. Anything else stops the bot with what is wrong."""
    if raw.strip().lower() in ("none", "off", ""):
        return {}
    out: dict[str, str] = {}
    for pair in raw.split(","):
        name, sep, model = (part.strip() for part in pair.partition("="))
        provider, slash, rest = model.partition("/")
        if not (sep and name and provider and slash and rest) or name in out or " " in model:
            msg = (
                f"COMPANION_JUDGE_ROUTES: {pair.strip()!r} is not judge=provider/model"
                " (or the judge is named twice)"
            )
            raise SystemExit(msg)
        out[name] = model
    return out


@dataclass(frozen=True, slots=True)
class Settings:
    switches: Mapping[str, str]  # by startup-line label
    daily_cap: float | None
    pace: str
    openrouter: bool  # whether an OpenRouter key is set
    everyday_model: str
    roleplay_model: str | None  # None: the everyday model plays scenes too
    everyday_standby: str | None  # answers when the everyday talker fails or stalls (J21)
    embed_model: str
    judge_routes: Mapping[str, str]  # judge name to the model it reads on first

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        stale = [f"{old} is now {new}" for old, new in RENAMED.items() if old in env]
        if stale:
            raise SystemExit("renamed settings, change them in .env: " + "; ".join(stale))
        has_key = bool(env.get("OPENROUTER_API_KEY"))
        roleplay = env.get("COMPANION_ROLEPLAY_MODEL", ROLEPLAY_MODEL)
        standby = env.get("COMPANION_EVERYDAY_STANDBY", "").strip()
        pace = env.get("COMPANION_PACE", "").strip().lower()
        return cls(
            switches={s.label: s.read(env) for s in SWITCHES},
            daily_cap=_daily_cap(env.get("COMPANION_DAILY_CAP_USD", "")),
            pace=pace if pace in PACES else DEFAULT_PACE,
            openrouter=has_key,
            everyday_model=env.get("COMPANION_EVERYDAY_MODEL")
            or (openrouter.DEFAULT_MODEL if has_key else anthropic.DEFAULT_MODEL),
            roleplay_model=None if roleplay.lower() == "none" or not has_key else roleplay,
            everyday_standby=None
            if not has_key or standby.lower() == "none"
            else standby or roleplay,
            embed_model=env.get("COMPANION_EMBED_MODEL", embeddings.DEFAULT_MODEL),
            judge_routes=_judge_routes(env.get("COMPANION_JUDGE_ROUTES", JUDGE_ROUTES)),
        )

    def position(self, label: str) -> str:
        """A switch's position: on, off or shadow, or the value it names."""
        return self.switches[_BY_LABEL[label].label]

    def on(self, label: str) -> bool:
        """Whether a switch is anything but off."""
        return self.position(label) != "off"

    @property
    def cap_text(self) -> str:
        return "off" if self.daily_cap is None else f"${self.daily_cap:.2f}"

    @property
    def pace_factor(self) -> float:
        return pace_factor(self.pace)

    def fragments(self) -> list[str]:
        """The startup line's settings part, `label value` each."""
        out = [
            f"roleplay {self.roleplay_model or 'the same model'}",
            *(
                [f"judges {','.join(f'{k}={v}' for k, v in self.judge_routes.items())}"]
                if self.judge_routes
                else []
            ),
            f"daily cap {self.cap_text}",
            f"pace {self.pace}",
        ]
        for s in SWITCHES:
            value = self.switches[s.label]
            out.append(f"{s.label} {(s.shown or {}).get(value, value)}")
            if s.label == "relevance":
                out.append(f"everyday standby {self.everyday_standby or 'off'}")
        return out
