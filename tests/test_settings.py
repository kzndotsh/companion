from __future__ import annotations

import re
from pathlib import Path

import pytest

from companion.settings import RENAMED, ROLEPLAY_MODEL, SWITCHES, Settings, Switch


def test_every_switch_reads_on_and_off_the_same_way() -> None:
    for word in ("off", "0", "no", "FALSE"):
        s = Settings.from_env({sw.env: word for sw in SWITCHES})
        assert all(not s.on(sw.label) for sw in SWITCHES if "off" in sw.values), word
    on = Settings.from_env({sw.env: "yes" for sw in SWITCHES})
    assert on.position("intimate") == "on"
    assert on.position("initiative") == "shadow"  # it has no live mode: anything but off is shadow


@pytest.mark.parametrize(
    ("raw", "platform"),
    [("", "telegram"), ("Discord", "discord"), ("off", "telegram"), ("on", "telegram")],
)
def test_the_platform_is_telegram_unless_discord_is_named(raw: str, platform: str) -> None:
    assert Settings.from_env({"COMPANION_PLATFORM": raw}).position("platform") == platform


def test_unset_is_the_default() -> None:
    blank = Settings.from_env({sw.env: " " for sw in SWITCHES})
    assert blank.switches == {sw.label: sw.values[0] for sw in SWITCHES}


@pytest.mark.parametrize("switch", SWITCHES, ids=lambda sw: sw.env)
def test_a_value_it_does_not_know_stops_the_bot_and_says_what_it_takes(switch: Switch) -> None:
    with pytest.raises(SystemExit, match=f"{switch.env}='shdow' is not a value it knows"):
        Settings.from_env({switch.env: "shdow"})


def test_models_follow_the_key_and_none() -> None:
    no_key = Settings.from_env({})
    assert (no_key.roleplay_model, no_key.everyday_standby) == (None, None)
    keyed = Settings.from_env({"OPENROUTER_API_KEY": "k"})
    assert keyed.roleplay_model == keyed.everyday_standby == ROLEPLAY_MODEL
    off = Settings.from_env(
        {
            "OPENROUTER_API_KEY": "k",
            "COMPANION_ROLEPLAY_MODEL": "none",
            "COMPANION_EVERYDAY_STANDBY": "none",
        }
    )
    assert (off.roleplay_model, off.everyday_standby) == (None, None)
    no_roleplay = Settings.from_env({"OPENROUTER_API_KEY": "k", "COMPANION_ROLEPLAY_MODEL": "None"})
    assert (no_roleplay.roleplay_model, no_roleplay.everyday_standby) == (None, None)


def test_the_risk_judge_reads_on_deepseek_by_default() -> None:
    assert Settings.from_env({}).judge_routes == {"crisis": "deepseek/deepseek-v4.1-flash"}
    assert Settings.from_env({"COMPANION_JUDGE_ROUTES": "none"}).judge_routes == {}
    assert Settings.from_env({"COMPANION_JUDGE_ROUTES": ""}).judge_routes == {}


def test_judge_models_parse_as_name_and_model_pairs() -> None:
    s = Settings.from_env({"COMPANION_JUDGE_ROUTES": " crisis = a/b , listen=c/d:free "})
    assert s.judge_routes == {"crisis": "a/b", "listen": "c/d:free"}


@pytest.mark.parametrize(
    "raw",
    ["crisis", "crisis=", "=a/b", "crisis=deepseek", "crisis=a/", "a=b/c,a=d/e", "x=a b/c"],
)
def test_junk_judge_models_stop_with_what_is_wrong(raw: str) -> None:
    with pytest.raises(SystemExit, match="COMPANION_JUDGE_ROUTES"):
        Settings.from_env({"COMPANION_JUDGE_ROUTES": raw})


@pytest.mark.parametrize(("old", "new"), list(RENAMED.items()))
def test_a_renamed_setting_still_set_stops_the_bot_with_its_new_name(old: str, new: str) -> None:
    with pytest.raises(SystemExit, match=f"{old} is now {new}"):
        Settings.from_env({old: "on"})


def test_every_switch_has_its_own_label() -> None:
    labels = [s.label for s in SWITCHES]
    assert len(labels) == len(set(labels))


def test_every_switch_the_code_asks_for_exists() -> None:
    """A label is a string, so a renamed switch only fails when the line runs (the memory pass asked
    for one by its old name and failed every time)."""
    labels = {s.label for s in SWITCHES}
    src = Path(__file__).parents[1] / "src" / "companion"
    asked = {
        (f.name, m)
        for f in src.rglob("*.py")
        for m in re.findall(r"\.(?:on|position)\(\"([^\"]+)\"\)", f.read_text())
    }
    assert asked
    assert {(name, m) for name, m in asked if m not in labels} == set()
