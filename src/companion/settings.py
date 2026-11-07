"""What the bot runs with, read from the environment once (`.env`, README's table).

Every switch is one row of a table in `core/switch.py`: its variable, its name on the startup block,
the values it takes and its default. "off", "0", "no" and "false" mean off and "on", "1", "yes" and
"true" mean on for every switch; anything else is the default. The startup block is printed from
the same values the bot is configured with, so the two cannot drift. Keys and tokens are not
settings: they are read where a client is made and never kept here.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from companion.core import switch as sw
from companion.core.reachout import Dial, dial
from companion.core.switch import SWITCHES, Mode, Switch
from companion.io.pace import DEFAULT_PACE, PACES, pace_factor
from companion.models import anthropic, embeddings, openrouter

DATA_DIR = Path("data")  # the data folder `companion run --data` and the evals default to
ROLEPLAY_MODEL = openrouter.DEEPSEEK
JUDGE_MODEL = openrouter.HAIKU
JUDGE_STANDBY = openrouter.DEEPSEEK  # asked only when the judges' model refuses
DEFAULT_DAILY_CAP_USD = 10.0
# The crisis risk judge reads on DeepSeek first: Haiku's provider refused many crisis messages
# (judge bake-off, evals/CHANGELOG.md, 2026-10-25). Haiku answers when DeepSeek refuses.
JUDGE_ROUTES = f"crisis={openrouter.DEEPSEEK}"

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
    switches: Mapping[Switch, str]  # each switch's position, by the row
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
            switches={s: s.read(env) for s in SWITCHES},
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
        return self.switches[switch]

    def mode(self, switch: Switch) -> Mode:
        """The position of a switch that takes on, shadow or off."""
        return Mode(self.switches[switch])

    def on(self, switch: Switch) -> bool:
        """Whether a switch is anything but off."""
        return self.switches[switch] != Mode.OFF

    def modes(self) -> Mapping[Switch, Mode]:
        """Every on, shadow or off switch's position: what the `Runtime` carries."""
        return {s: Mode(v) for s, v in self.switches.items() if s.is_mode}

    @property
    def reach(self) -> Dial:
        """The reach-out dial (`COMPANION_REACH`)."""
        return dial(self.switches[sw.REACH])

    @property
    def scene_model(self) -> str:
        """The model that plays scenes: the roleplay model, or the everyday one when none is set."""
        return self.roleplay_model or self.everyday_model

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
            if s.shown is None and s.is_mode:
                value = Mode(self.switches[s])
                out["live" if value is Mode.ON else value.value].append(s.label)
        return out

    def dials(self) -> list[str]:
        """The switches that take a value of their own, `label value` each, the platform aside."""
        return [
            f"{s.label} {(s.shown or {}).get(v, v)}"
            for s in SWITCHES
            if s.label != "platform" and not (s.shown is None and s.is_mode)
            for v in (self.switches[s],)
        ]
