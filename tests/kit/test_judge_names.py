"""Every model call is a judge asked through `kit/ask.py` (AGENTS.md). A judge's name is the log's
name for it and the key `COMPANION_JUDGE_ROUTES` routes by, so two judges must not share one."""

from __future__ import annotations

import ast
import importlib
from collections import defaultdict
from pathlib import Path

import pytest

from companion.kit.ask import check_routes, declared_judges
from companion.settings import Settings

importlib.import_module("companion.daemon")  # loads every module that declares a judge

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


def test_every_name_a_judge_is_asked_under_is_declared() -> None:
    """A `Judge` declares its own name; a `read_times` call passes a name declared with
    `judge_name` (a literal would be a name `COMPANION_JUDGE_ROUTES` could not check)."""
    asked: set[str] = set()
    for path, tree in _trees().items():
        if path.startswith("features/audits/"):  # run by the audit commands, never by the bot
            continue
        for call in _calls(tree, "Judge") + _calls(tree, "yes_no_judge"):
            first = call.args[0] if call.args else None
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                asked.add(first.value)
        for call in _calls(tree, "read_times"):
            spend = next((k.value for k in call.keywords if k.arg == "spend"), None)
            assert isinstance(spend, ast.Name), (
                f"{path}:{call.lineno}: pass `spend` a name declared with `judge_name`"
            )
    declared = declared_judges()
    assert asked <= declared, f"asked under a name nobody declared: {sorted(asked - declared)}"
    assert {"crisis", "floor-minor", "worth", "scene memory"} <= declared


def test_the_default_routes_name_judges_that_exist() -> None:
    check_routes(Settings.from_env({}).judge_routes)


def test_a_route_that_names_no_judge_stops_the_bot_and_lists_the_ones_it_knows() -> None:
    with pytest.raises(SystemExit, match=r"crysis.*the judges are .*crisis"):
        check_routes({"crysis": "x/y"})
