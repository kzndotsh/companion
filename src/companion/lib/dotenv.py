"""Reading a `.env` file into the environment, before anything reads a setting."""

from __future__ import annotations

import os
import re
from pathlib import Path


def load_dotenv(path: Path) -> None:
    """KEY=value lines; a quoted value is kept whole, an unquoted one ends at a ` #` comment."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and not line.lstrip().startswith("#"):
            value = value.strip()
            if value[:1] in ("'", '"'):
                value = value.strip("\"'")
            else:
                value = re.split(r"\s#", value, maxsplit=1)[0].strip()
            os.environ.setdefault(key.strip(), value)
