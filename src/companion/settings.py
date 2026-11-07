"""What the bot runs with, read from the environment once (`.env`, README's table).

Every switch is one row of a table: its variable, its name on the startup block, the values it takes
and its default. "off", "0", "no" and "false" mean off and "on", "1", "yes" and "true" mean on for
every switch; anything else is the default. The startup block is printed from the same values the
bot is configured with, so the two cannot drift. Keys and tokens are not settings: they are read
where a client is made and never kept here.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from companion.core.reachout import DEFAULT_DIAL, Dial
from companion.io.pace import DEFAULT_PACE, PACES, pace_factor
from companion.models import anthropic, embeddings, openrouter

ROLEPLAY_MODEL = openrouter.DEEPSEEK
JUDGE_MODEL = openrouter.HAIKU
JUDGE_STANDBY = openrouter.DEEPSEEK  # asked only when the judges' model refuses
DEFAULT_DAILY_CAP_USD = 10.0
# The crisis risk judge reads on DeepSeek first: Haiku's provider refused many crisis messages
# (judge bake-off, evals/CHANGELOG.md, 2026-10-25). Haiku answers when DeepSeek refuses.
JUDGE_ROUTES = f"crisis={openrouter.DEEPSEEK}"

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
    "COMPANION_SCENE_MEMORY": "COMPANION_INTIMATE_MEMORY",
    "COMPANION_RESAMPLE": "COMPANION_REDRAW",
    "COMPANION_MARKS": "COMPANION_OWN_MARKS",
}


@dataclass(frozen=True, slots=True)
class Switch:
    env: str
    label: str  # its name on the startup block
    values: tuple[str, ...]  # the first is the default
    shown: Mapping[str, str] | None = None  # how a value reads on the startup block, when not as is

    def read(self, environ: Mapping[str, str]) -> str:
        """Unset is the default, and an on or off word on a switch without that position (on for one
        with no live mode) is its first one. Any other value it does not know stops the bot: a typo
        used to become the default without a word."""
        raw = environ.get(self.env, "").strip().lower()
        value = "off" if raw in OFF else "on" if raw in ON else raw
        if value in self.values:
            return value
        if raw and value not in ("on", "off"):
            msg = f"{self.env}={raw!r} is not a value it knows: {', '.join(self.values)}"
            raise SystemExit(msg)
        return self.values[0]


# One name per switch: a use names the row itself, so a typo fails at import or type-check time and
# a new switch is one row here, its place in SWITCHES and its uses.
PLATFORM = Switch(
    "COMPANION_PLATFORM", "platform", ("telegram", "discord")
)  # which chat it runs on
SPLIT = Switch("COMPANION_SPLIT", "split", ("on", "off"))
LISTEN = Switch("COMPANION_LISTEN", "listen", ("on", "off"))
INITIATIVE = Switch("COMPANION_INITIATIVE", "initiative", ("shadow", "off"))
MOOD = Switch("COMPANION_MOOD", "mood", ("on", "shadow", "off"))
REDRAW = Switch("COMPANION_REDRAW", "redraw", ("on", "off"))
ROUTE_INTIMATE = Switch(
    "COMPANION_ROUTE_INTIMATE", "intimate", ("off", "on"), {"on": "may route", "off": "stays"}
)
RELEVANCE = Switch("COMPANION_RELEVANCE", "relevance", ("on", "shadow", "off"))
REREAD = Switch("COMPANION_REREAD", "re-read", ("on", "shadow", "off"))
PROMISES = Switch("COMPANION_PROMISES", "promises", ("shadow", "off"))
LORE = Switch("COMPANION_LORE", "lore", ("on", "shadow", "off"))
FOCUS = Switch("COMPANION_FOCUS", "focus", ("on", "off"))
REMINDERS = Switch("COMPANION_REMINDERS", "reminders", ("on", "off"))
EPISODES = Switch("COMPANION_EPISODES", "episodes", ("on", "shadow", "off"))
OWN_MARKS = Switch("COMPANION_OWN_MARKS", "own marks", ("on", "off"))
HEDGED_PLANS = Switch("COMPANION_HEDGED_PLANS", "hedged plans", ("loose", "off"), {"off": "strict"})
REACH = Switch(
    "COMPANION_REACH",
    "reach",
    (DEFAULT_DIAL.value, *(d.value for d in Dial if d is not DEFAULT_DIAL)),
)
CRISIS = Switch("COMPANION_CRISIS", "crisis", ("on", "shadow", "off"))
CALENDAR = Switch("COMPANION_CALENDAR", "calendar", ("on", "off"))
NOW = Switch("COMPANION_NOW", "now", ("shadow", "on", "off"))
HISTORY = Switch("COMPANION_HISTORY", "history", ("shadow", "on", "off"))
INTIMATE_MEMORY = Switch("COMPANION_INTIMATE_MEMORY", "intimate memory", ("on", "shadow", "off"))

# In the order they appear on the startup block, within its rows.
SWITCHES: tuple[Switch, ...] = (
    PLATFORM,
    SPLIT,
    LISTEN,
    INITIATIVE,
    MOOD,
    REDRAW,
    ROUTE_INTIMATE,
    RELEVANCE,
    REREAD,
    PROMISES,
    LORE,
    FOCUS,
    REMINDERS,
    EPISODES,
    OWN_MARKS,
    HEDGED_PLANS,
    REACH,
    CRISIS,
    CALENDAR,
    NOW,
    HISTORY,
    INTIMATE_MEMORY,
)


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
    switches: Mapping[str, str]  # by its label
    daily_cap: float | None
    pace: str
    openrouter: bool  # whether an OpenRouter key is set
    everyday_model: str
    roleplay_model: str | None  # None: the everyday model plays scenes too
    everyday_standby: str | None  # answers when the everyday talker fails or stalls (J21)
    embed_model: str
    judge_routes: Mapping[str, str]  # judge name to the model it reads on first
    judge_model: str  # the judges' and the memory pass's model
    judge_standby: str | None  # asked only when the judge model refuses; None: no standby
    backup_dir: Path | None  # None: data/backups
    character: str | None  # the sheet COMPANION_CHARACTER names
    db: Path | None  # the CLI's database; None: the one in data/
    kiro_url: str  # the local Kiro gateway, for evals
    kiro_key: str

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        stale = [f"{old} is now {new}" for old, new in RENAMED.items() if old in env]
        if stale:
            raise SystemExit("renamed settings, change them in .env: " + "; ".join(stale))
        has_key = bool(env.get("OPENROUTER_API_KEY"))
        roleplay = env.get("COMPANION_ROLEPLAY_MODEL", ROLEPLAY_MODEL)
        standby = env.get("COMPANION_EVERYDAY_STANDBY", "").strip() or roleplay
        pace = env.get("COMPANION_PACE", "").strip().lower()
        judge_standby = env.get("COMPANION_JUDGE_STANDBY", JUDGE_STANDBY)
        backup = env.get("COMPANION_BACKUP_DIR", "").strip()
        db = env.get("COMPANION_DB")
        return cls(
            switches={s.label: s.read(env) for s in SWITCHES},
            daily_cap=_daily_cap(env.get("COMPANION_DAILY_CAP_USD", "")),
            pace=pace if pace in PACES else DEFAULT_PACE,
            openrouter=has_key,
            everyday_model=env.get("COMPANION_EVERYDAY_MODEL")
            or (openrouter.DEFAULT_MODEL if has_key else anthropic.DEFAULT_MODEL),
            roleplay_model=None if roleplay.lower() == "none" or not has_key else roleplay,
            everyday_standby=None if not has_key or standby.lower() == "none" else standby,
            embed_model=env.get("COMPANION_EMBED_MODEL", embeddings.DEFAULT_MODEL),
            judge_routes=_judge_routes(env.get("COMPANION_JUDGE_ROUTES", JUDGE_ROUTES)),
            judge_model=env.get("COMPANION_JUDGE_MODEL", JUDGE_MODEL),
            judge_standby=None if judge_standby.lower() == "none" else judge_standby,
            backup_dir=Path(backup).expanduser() if backup else None,
            character=env.get("COMPANION_CHARACTER", "").strip() or None,
            db=Path(db) if db else None,
            kiro_url=env.get("KIRO_GATEWAY_URL", "http://127.0.0.1:9000"),
            kiro_key=env.get("KIRO_GATEWAY_API_KEY") or env.get("PROXY_API_KEY", ""),
        )

    def position(self, switch: Switch) -> str:
        """A switch's position: on, off or shadow, or the value it names."""
        return self.switches[switch.label]

    def on(self, switch: Switch) -> bool:
        """Whether a switch is anything but off."""
        return self.position(switch) != "off"

    @property
    def cap_text(self) -> str:
        return "off" if self.daily_cap is None else f"${self.daily_cap:.2f}"

    @property
    def pace_factor(self) -> float:
        return pace_factor(self.pace)

    def states(self) -> dict[str, list[str]]:
        """The on, shadow and off switches by where they stand, in startup order. A switch that
        takes another value (a platform, a dial, a routing choice) is in `dials` instead."""
        out: dict[str, list[str]] = {"live": [], "shadow": [], "off": []}
        for s in SWITCHES:
            value = self.switches[s.label]
            if s.shown is None and set(s.values) <= {"on", "shadow", "off"}:
                out["live" if value == "on" else value].append(s.label)
        return out

    def dials(self) -> list[str]:
        """The switches that take a value of their own, `label value` each, the platform aside."""
        return [
            f"{s.label} {(s.shown or {}).get(v, v)}"
            for s in SWITCHES
            if s.label != "platform"
            and not (s.shown is None and set(s.values) <= {"on", "shadow", "off"})
            for v in (self.switches[s.label],)
        ]
