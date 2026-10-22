from __future__ import annotations

import re
import subprocess
from pathlib import Path

LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def test_every_relative_link_in_the_docs_points_at_a_file_that_exists() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "*.md"], capture_output=True, text=True, check=True
    ).stdout.split()
    broken = [
        f"{doc} -> {target}"
        for doc in tracked
        for target in LINK.findall(Path(doc).read_text(encoding="utf-8"))
        if not target.startswith(("http://", "https://", "mailto:"))
        and not (Path(doc).parent / target).exists()
    ]
    assert broken == []
