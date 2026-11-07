"""Every model call is a judge asked through `kit/ask.py` (AGENTS.md). A judge's name is the log's
name for it and the key `COMPANION_JUDGE_ROUTES` routes by, so two judges must not share one."""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "companion"

# The only places a structured model is called directly: the door, the wrappers that meter and
# route it, and the eval runner's own plumbing.
MAY_EXTRACT = {
    "kit/ask.py",
    "models/fallback.py",
    "core/spend.py",
    "evals/judge.py",
    "evals/runner.py",
}


def _calls(tree: ast.Module, name: str) -> list[ast.Call]:
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name
    ]


def _trees() -> dict[str, ast.Module]:
    return {
        str(p.relative_to(SRC)): ast.parse(p.read_text(encoding="utf-8"))
        for p in sorted(SRC.rglob("*.py"))
    }


def test_every_judge_is_a_module_constant_with_a_name_of_its_own() -> None:
    named: dict[str, list[str]] = defaultdict(list)
    for path, tree in _trees().items():
        constants = {
            id(n.value)
            for n in tree.body
            if isinstance(n, ast.Assign | ast.AnnAssign) and isinstance(n.value, ast.Call)
        }
        for call in _calls(tree, "Judge"):
            if path == "kit/ask.py":
                continue
            assert id(call) in constants, (
                f"{path}:{call.lineno}: a Judge is declared at module level"
            )
            first = call.args[0]
            assert isinstance(first, ast.Constant) and isinstance(first.value, str), (
                f"{path}:{call.lineno}: a Judge's first argument is its name, as a string"
            )
            named[first.value].append(f"{path}:{call.lineno}")
    shared = {name: where for name, where in named.items() if len(where) > 1}
    assert not shared, f"judges that share a name cannot be routed or costed apart: {shared}"


def test_no_model_is_called_outside_the_door() -> None:
    for path, tree in _trees().items():
        if path in MAY_EXTRACT:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                assert n.func.attr != "extract", f"{path}:{n.lineno}: ask a judge through `ask`"
