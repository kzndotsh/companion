"""The console script's start: `.env` is read first, then the CLI is imported. Modules read prompt
overrides when they are imported, so the file has to be in the environment before any of them."""

from __future__ import annotations

import importlib
from pathlib import Path

from companion.lib.dotenv import load_dotenv


def main() -> None:
    load_dotenv(Path(".env"))
    importlib.import_module("companion.cli.main").main()
