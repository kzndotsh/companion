"""Every prompt the bot sends, as versioned text files.

A prompt is a name and a version: `system/ack/v1.md`. The manifest says which version is current.
A shipped version is never edited; a change is a new file with an entry in `CHANGELOG.md`, so what
changed is visible and a bad change is one line to undo. Each judgement and decision that uses a
prompt logs `name@version`. Some prompts hold placeholders written `$name`, which code fills in
with `render`.

The folders say what a prompt is. `system/` holds the system prompts, `notes/` the lines added to
the talker's system block each turn, `messages/` text sent to the user.

`COMPANION_PROMPT_OVERRIDES="system/ack=v2,notes/length=v3"` picks other versions for an
experiment. It is read when a prompt is first loaded, so set it before the process starts.
"""

from __future__ import annotations

from importlib import resources

from companion.lib.prompts import Library

OVERRIDES_ENV = "COMPANION_PROMPT_OVERRIDES"
_LIBRARY = Library(resources.files(__package__), OVERRIDES_ENV)

manifest = _LIBRARY.manifest
versions = _LIBRARY.versions
get = _LIBRARY.get
current = _LIBRARY.current
set_hash = _LIBRARY.set_hash
