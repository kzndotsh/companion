from __future__ import annotations

import logging
from pathlib import Path

import pytest

from companion.lib import logs


@pytest.fixture(autouse=True)
def _clean_root() -> object:
    yield
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_companion", False):
            root.removeHandler(handler)
            handler.close()


def test_only_credential_looking_variables_are_secrets() -> None:
    env = {
        "TELEGRAM_BOT_TOKEN": "123456:abcdefgh",
        "OPENROUTER_API_KEY": "sk-or-v1-longvalue",
        "HOME": "/home/someone",
        "SHORT_KEY": "abc",
    }
    assert set(logs.secrets_in(env)) == {"123456:abcdefgh", "sk-or-v1-longvalue"}


def test_a_secret_never_reaches_the_file_even_in_a_traceback(tmp_path: Path) -> None:
    path = logs.configure(tmp_path, {"TELEGRAM_BOT_TOKEN": "123456:abcdefgh"})
    log = logging.getLogger("companion.test")
    log.warning("calling https://api.telegram.org/bot123456:abcdefgh/getUpdates")
    log.warning("token is %s", "123456:abcdefgh")
    try:
        raise RuntimeError("failed for 123456:abcdefgh")
    except RuntimeError:
        log.exception("boom")
    for handler in logging.getLogger().handlers:
        handler.flush()
    text = path.read_text(encoding="utf-8")
    assert "123456:abcdefgh" not in text
    assert text.count("[redacted]") >= 4


def test_the_file_keeps_debug_and_the_console_does_not(tmp_path: Path) -> None:
    path = logs.configure(tmp_path, {})
    logging.getLogger("companion.test").debug("a detail only the file keeps")
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert "a detail only the file keeps" in path.read_text(encoding="utf-8")
    levels = {h.level for h in logging.getLogger().handlers if getattr(h, "_companion", False)}
    assert logging.INFO in levels
    assert logging.DEBUG in levels


def test_httpx_stays_quiet_and_calling_twice_does_not_double_the_handlers(
    tmp_path: Path,
) -> None:
    logs.configure(tmp_path, {})
    logs.configure(tmp_path, {})
    ours = [h for h in logging.getLogger().handlers if getattr(h, "_companion", False)]
    assert len(ours) == 2
    assert logging.getLogger("httpx").level == logging.WARNING
