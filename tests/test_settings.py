from __future__ import annotations

import pytest

from companion.settings import ROLEPLAY_MODEL, SWITCHES, Settings


def test_every_switch_reads_on_and_off_the_same_way() -> None:
    for word in ("off", "0", "no", "FALSE"):
        s = Settings.from_env({sw.env: word for sw in SWITCHES})
        assert all(not s.on(sw.label) for sw in SWITCHES if "off" in sw.values), word
    on = Settings.from_env({sw.env: "yes" for sw in SWITCHES})
    assert on.mode("intimate") == "on"
    assert on.mode("initiative") == "shadow"  # it has no live mode: anything but off is shadow


@pytest.mark.parametrize(
    ("raw", "surface"),
    [("", "telegram"), ("Discord", "discord"), ("off", "telegram"), ("x", "telegram")],
)
def test_the_surface_is_telegram_unless_discord_is_named(raw: str, surface: str) -> None:
    assert Settings.from_env({"COMPANION_SURFACE": raw}).mode("surface") == surface


def test_unset_or_unknown_is_the_default() -> None:
    blank = Settings.from_env({})
    junk = Settings.from_env({sw.env: "junk" for sw in SWITCHES})
    assert blank.switches == junk.switches == {sw.label: sw.values[0] for sw in SWITCHES}


def test_models_follow_the_key_and_none() -> None:
    no_key = Settings.from_env({})
    assert (no_key.roleplay_model, no_key.talker_fallback) == (None, None)
    keyed = Settings.from_env({"OPENROUTER_API_KEY": "k"})
    assert keyed.roleplay_model == keyed.talker_fallback == ROLEPLAY_MODEL
    off = Settings.from_env(
        {
            "OPENROUTER_API_KEY": "k",
            "COMPANION_ROLEPLAY_MODEL": "none",
            "COMPANION_TALKER_FALLBACK": "none",
        }
    )
    assert (off.roleplay_model, off.talker_fallback) == (None, None)


def test_the_risk_judge_reads_on_deepseek_by_default() -> None:
    assert Settings.from_env({}).judge_models == {"crisis": "deepseek/deepseek-v4.1-flash"}
    assert Settings.from_env({"COMPANION_JUDGE_MODELS": "none"}).judge_models == {}
    assert Settings.from_env({"COMPANION_JUDGE_MODELS": ""}).judge_models == {}


def test_judge_models_parse_as_name_and_model_pairs() -> None:
    s = Settings.from_env({"COMPANION_JUDGE_MODELS": " crisis = a/b , listen=c/d:free "})
    assert s.judge_models == {"crisis": "a/b", "listen": "c/d:free"}


@pytest.mark.parametrize(
    "raw",
    ["crisis", "crisis=", "=a/b", "crisis=deepseek", "crisis=a/", "a=b/c,a=d/e", "x=a b/c"],
)
def test_junk_judge_models_stop_with_what_is_wrong(raw: str) -> None:
    with pytest.raises(SystemExit, match="COMPANION_JUDGE_MODELS"):
        Settings.from_env({"COMPANION_JUDGE_MODELS": raw})
