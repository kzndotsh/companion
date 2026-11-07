"""`.env` reaches the process before any companion module is imported. It used to be read in
`daemon.run`, after modules that read a prompt when they are imported had already read it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROBE = """
import sys
from companion.entry import main

sys.argv = ["companion", "--help"]
try:
    main()
except SystemExit:
    pass
print(sys.modules["companion.features.crisis.logic"].CONCERN.version)
"""


def test_a_prompt_override_set_only_in_dotenv_reaches_a_prompt_read_at_import(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text("COMPANION_PROMPT_OVERRIDES=notes/crisis-concern=v1\n")
    out = subprocess.run(  # our own interpreter and a fixed script
        [sys.executable, "-c", PROBE],
        cwd=tmp_path,
        env={"PYTHONPATH": ":".join(sys.path)},
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.splitlines()[-1] == "v1"  # the manifest says v2
