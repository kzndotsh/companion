from __future__ import annotations

import dataclasses
from pathlib import Path

from companion import compose
from companion.core import switch as sw
from companion.core.switch import Mode
from companion.kit.runtime import Runtime
from companion.settings import Settings
from companion.store.sqlite.store import Store
from tests.turn.test_mood_loop import PREFIX, REL, Talker

PARTS = {
    "judge",
    "memory",
    "tics",
    "roleplay_talker",
    "roleplay_prefix",
    "embedder",
    "embed_model",
    "scene_reminder",
    "serious_message",
}


def test_a_runtime_switch_has_no_default_of_its_own() -> None:
    """Every switch field is required, so it is `Settings` that says what it is."""
    defaulted = {
        f.name
        for f in dataclasses.fields(Runtime)
        if f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING
    }
    assert defaulted <= PARTS


def test_a_runtime_is_made_only_by_compose() -> None:
    src = Path(__file__).parents[1] / "src" / "companion"
    made = {
        f.relative_to(src).as_posix()
        for f in src.rglob("*.py")
        if "Runtime(" in f.read_text() and f.name != "runtime.py"
    }
    assert made == {"compose.py"}


def test_a_runtime_reads_every_switch_as_settings_has_it(tmp_path: Path) -> None:
    store = Store(tmp_path / "c.sqlite")
    try:
        live = compose.runtime(Settings.from_env({}), store, Talker(), PREFIX, REL)
        assert (
            live.mode(sw.MOOD),
            live.mode(sw.CRISIS),
            live.on(sw.REDRAW),
            live.daily_cap_usd,
        ) == (
            Mode.ON,
            Mode.ON,
            True,
            10.0,
        )
        quiet = compose.runtime(
            Settings.from_env({sw.MOOD.env: "off"}), store, Talker(), PREFIX, REL
        )
        assert quiet.mode(sw.MOOD) is Mode.OFF
    finally:
        store.close()


def test_the_bots_memory_pass_and_the_command_are_built_by_one_function() -> None:
    """The steps the features add (its own history, the scene memory) come from `after_pass`, and
    what the settings switch on is in the options, whoever asks."""
    on = Settings.from_env({sw.HISTORY.env: "shadow", sw.INTIMATE_MEMORY.env: "on"})
    off = Settings.from_env({sw.HISTORY.env: "off", sw.INTIMATE_MEMORY.env: "off"})
    assert len(compose.pass_options(on, None, None, "sheet").parts.steps) == 2  # type: ignore[arg-type]
    assert compose.pass_options(off, None, None).parts.steps == ()  # type: ignore[arg-type]
    options = compose.pass_options(Settings.from_env({sw.PROMISES.env: "shadow"}), None, None)  # type: ignore[arg-type]
    assert len(options.parts.loops) == 1  # the open-loop read, with the promise read riding it
    assert options.embed is None
    assert options.parts.writes[0].same is None  # type: ignore[attr-defined]
