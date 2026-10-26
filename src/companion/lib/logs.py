"""Where the logs go. The console keeps the short INFO view; a rotating file keeps everything.

The file is for debugging: every stage of a turn, every judge, every model call and every Telegram
or Discord call, at DEBUG. Secrets (any variable ending in _TOKEN or _KEY, both bot tokens among
them) are scrubbed from both outputs by value, so a token that slips into an error message or a URL
never reaches a log. What people said is logged in full on purpose; this is
a single-user local project, and the file lives under `data/`, which is not committed.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE = "companion.log"
MAX_BYTES = 5_000_000
BACKUPS = 5
MIN_SECRET_CHARS = 8
SECRET_SUFFIXES = ("_KEY", "_TOKEN", "_SECRET", "_PASSWORD")
FORMAT = "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s: %(message)s"
DATE_FORMAT = "%H:%M:%S"
FILE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
NOISY = ("httpx", "httpcore", "hpack", "asyncio", "discord")


def secrets_in(env: Mapping[str, str]) -> list[str]:
    """Values of every environment variable that looks like a credential, longest first so a
    value that contains another is scrubbed whole."""
    found = {
        value
        for name, value in env.items()
        if name.upper().endswith(SECRET_SUFFIXES) and len(value) >= MIN_SECRET_CHARS
    }
    return sorted(found, key=len, reverse=True)


class Redactor(logging.Filter):
    """Replaces each secret with a marker in the finished message and its traceback."""

    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self._secrets = secrets

    def scrub(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, "[redacted]")
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        if self._secrets:
            record.msg = self.scrub(record.getMessage())
            record.args = None
            if record.exc_info:
                record.exc_text = self.scrub(logging.Formatter().formatException(record.exc_info))
                record.exc_info = None
        return True


def configure(log_dir: Path, env: Mapping[str, str] | None = None) -> Path:
    """Set up both outputs and return the log file. Safe to call twice: it replaces its handlers."""
    path = log_dir / LOG_FILE
    log_dir.mkdir(parents=True, exist_ok=True)
    redact = Redactor(secrets_in(os.environ if env is None else env))
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(FORMAT, DATE_FORMAT))
    console.addFilter(redact)
    file = RotatingFileHandler(path, maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8")
    file.setLevel(logging.DEBUG)
    file.setFormatter(logging.Formatter(FORMAT, FILE_DATE_FORMAT))
    file.addFilter(redact)
    root = logging.getLogger()
    for old in list(root.handlers):
        if getattr(old, "_companion", False):
            root.removeHandler(old)
    for handler in (console, file):
        handler._companion = True  # type: ignore[attr-defined]
        root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    # httpx logs full request URLs at INFO and Telegram puts the bot token in the URL; discord.py
    # logs every gateway event and request at DEBUG.
    for name in NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)
    return path
