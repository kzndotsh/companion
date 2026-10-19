"""The table, and a file that keeps every reply so scores can be audited by reading them."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from companion.evals.fixtures import Fixture
from companion.evals.runner import Results, Variant
from companion.evals.stats import Comparison, cmh, fisher, holm, wilson


def _counts(results: Results, fixture: str, variant: str) -> tuple[int, int]:
    cell = results.cells[(fixture, variant)]
    return cell.count("pass"), cell.count("pass") + cell.count("fail")


def _cell(results: Results, fixture: str, variant: str) -> str:
    cell = results.cells[(fixture, variant)]
    passed, scored = _counts(results, fixture, variant)
    text = f"{passed}/{scored}"
    if scored:
        lo, hi = wilson(passed, scored)
        text += f" {lo:.0%}-{hi:.0%}"
    if cell.count("unclear"):
        text += f" (+{cell.count('unclear')}?)"
    if cell.skipped:
        text += f" [{cell.skipped} skipped]"
    return text


def render_table(results: Results, fixtures: Sequence[Fixture], variants: Sequence[Variant]) -> str:
    width = max([len(f.id) for f in fixtures] + [7]) + 2
    col = max([len(v.label) for v in variants] + [12]) + 2
    lines = ["fixture".ljust(width) + "".join(v.label.ljust(col) for v in variants)]
    lines.extend(
        f.id.ljust(width) + "".join(_cell(results, f.id, v.label).ljust(col) for v in variants)
        for f in fixtures
    )
    total: list[str] = []
    for v in variants:
        cells = [results.cells[(f.id, v.label)] for f in fixtures]
        passed = sum(c.count("pass") for c in cells)
        scored = passed + sum(c.count("fail") for c in cells)
        total.append(f"{passed}/{scored}".ljust(col))
    lines += ["-" * (width + col * len(variants)), "total".ljust(width) + "".join(total)]
    note = f"spent ${results.spent:.4f} by the replies' own costs"
    if results.charged is not None:
        note += f", OpenRouter charged ${results.charged:.4f} (the whole account, the bot included)"
    if results.stopped_by_cap:
        note += "  STOPPED EARLY: the spend cap was reached, some samples were skipped"
    lines += [
        "",
        note,
        (
            "(n/m = passes out of scored samples, then the 95% range the true rate probably sits"
            " in. +k? = unscored because the judge was unclear)"
        ),
        *compare(results, fixtures, variants),
    ]
    return "\n".join(lines)


def compare(
    results: Results, fixtures: Sequence[Fixture], variants: Sequence[Variant]
) -> list[str]:
    """Every later variant against the first: per fixture, then the total compared within each
    fixture. Chances are adjusted for how many comparisons the run made."""
    if len(variants) < 2:
        return []
    base = variants[0].label
    pairs = [(f.id, v.label) for v in variants[1:] for f in fixtures]
    raw = [fisher(*_counts(results, f, base), *_counts(results, f, v)) for f, v in pairs]
    per_fixture = [
        Comparison(f"{f} ({v})", _counts(results, f, base), _counts(results, f, v), chance)
        for (f, v), chance in zip(pairs, holm(raw), strict=True)
    ]
    totals_raw = [
        cmh([(*_counts(results, f.id, base), *_counts(results, f.id, v.label)) for f in fixtures])
        for v in variants[1:]
    ]
    totals = [
        Comparison(
            f"total ({v.label})",
            _total(results, fixtures, base),
            _total(results, fixtures, v.label),
            chance,
        )
        for v, chance in zip(variants[1:], holm(totals_raw), strict=True)
    ]
    return ["", f"compared with {base}:", *(f"  {c.line()}" for c in [*per_fixture, *totals])]


def _total(results: Results, fixtures: Sequence[Fixture], variant: str) -> tuple[int, int]:
    counts = [_counts(results, f.id, variant) for f in fixtures]
    return sum(p for p, _ in counts), sum(n for _, n in counts)


def render_replies(
    results: Results, fixtures: Sequence[Fixture], variants: Sequence[Variant]
) -> str:
    out: list[str] = []
    for f in fixtures:
        out.append(f"\n=== {f.id}: {f.description}")
        for v in variants:
            for s in results.cells[(f.id, v.label)].samples:
                flat = s.reply.strip().replace("\n\n", " / ").replace("\n", " ")
                out.append(f"  [{v.label}] {s.outcome.upper():7} {flat}")
    return "\n".join(out)


def save(
    path: Path,
    results: Results,
    fixtures: Sequence[Fixture],
    variants: Sequence[Variant],
    judge_hash: str,
) -> None:
    payload = {
        "judge_hash": judge_hash,
        "spent_usd": results.spent,
        "charged_usd": results.charged,
        "stopped_by_cap": results.stopped_by_cap,
        "variants": [
            {"label": v.label, "prefix": v.prefix.sha256, "model": v.model} for v in variants
        ],
        "results": [
            {
                "fixture": f.id,
                "variant": v.label,
                "skipped": results.cells[(f.id, v.label)].skipped,
                "samples": [asdict(s) for s in results.cells[(f.id, v.label)].samples],
            }
            for f in fixtures
            for v in variants
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
