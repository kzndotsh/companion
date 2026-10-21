from __future__ import annotations

from companion.settings import ROLEPLAY_MODEL, SWITCHES, Settings


def test_every_switch_reads_on_and_off_the_same_way() -> None:
    for word in ("off", "0", "no", "FALSE"):
        s = Settings.from_env({sw.env: word for sw in SWITCHES})
        assert all(not s.on(sw.label) for sw in SWITCHES), word
    on = Settings.from_env({sw.env: "yes" for sw in SWITCHES})
    assert on.mode("intimate") == "on"
    assert on.mode("initiative") == "shadow"  # it has no live mode: anything but off is shadow


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
