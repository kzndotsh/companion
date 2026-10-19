from __future__ import annotations

import pytest

from companion.evals.fixtures import Fixture, MaxWords
from companion.evals.report import render_table
from companion.evals.runner import Cell, Results, Sample, Variant
from companion.evals.stats import Comparison, cmh, fisher, holm, samples_needed, wilson
from tests.evals.test_evals import PREFIX


def test_wilson_matches_the_textbook_interval() -> None:
    lo, hi = wilson(9, 12)
    assert (lo, hi) == pytest.approx((0.4677, 0.9111), abs=1e-4)
    assert wilson(12, 12)[1] == 1.0
    assert wilson(0, 0) == (0.0, 1.0)


def test_fisher_matches_the_tea_tasting_example() -> None:
    assert fisher(3, 4, 1, 4) == pytest.approx(0.4857, abs=1e-4)
    assert fisher(4, 30, 24, 30) < 0.001
    assert fisher(5, 5, 5, 5) == pytest.approx(1.0)


def test_holm_scales_by_rank_and_never_goes_down() -> None:
    assert holm([0.01, 0.04, 0.2]) == pytest.approx([0.03, 0.08, 0.2])
    assert holm([0.04, 0.01]) == pytest.approx([0.04, 0.02])


def test_the_pooled_total_compares_within_each_fixture() -> None:
    # each fixture alone favours B, so pooled it is clearer than either
    one = (5, 12, 9, 12)
    assert cmh([one, one, one]) < fisher(*one)
    # a fixture that is easy for both cannot make a gap on its own
    assert cmh([(12, 12, 12, 12)]) == 1.0


def test_samples_needed_for_a_ten_point_gap() -> None:
    assert samples_needed(0.5, 0.6) == pytest.approx(388, abs=2)
    assert samples_needed(0.5, 0.5) is None


def test_a_noisy_comparison_says_so_and_how_many_samples_would_tell() -> None:
    line = Comparison("f", (5, 12), (9, 12), 0.21).line()
    assert "within noise" in line
    assert "samples each" in line
    assert "a real difference" in Comparison("f", (4, 30), (24, 30), 0.0001).line()


def _results(a: int, b: int, n: int) -> Results:
    def cell(passed: int) -> Cell:
        c = Cell()
        for i in range(n):
            verdict = "pass" if i < passed else "fail"
            c.samples.append(Sample("x", (verdict,), 1, 0.0))
        return c

    return Results(cells={("f1", "a"): cell(a), ("f1", "b"): cell(b)})


def test_the_table_shows_ranges_and_compares_variants() -> None:
    f = Fixture(id="f1", description="d", script=None, checks=(MaxWords(5),))
    table = render_table(_results(4, 24, 30), [f], [Variant("a", PREFIX), Variant("b", PREFIX)])
    assert "4/30 5%-30%" in table
    assert "compared with a:" in table
    assert "f1 (b): 4/30 vs 24/30" in table
    assert "a real difference" in table
    single = render_table(_results(4, 24, 30), [f], [Variant("a", PREFIX)])
    assert "compared with" not in single
