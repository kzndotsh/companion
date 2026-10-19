"""Margins of error for pass rates, and whether two variants really differ (J17).

Pass rates here come from 12 to 30 samples, where the textbook normal interval is badly off, so a
single cell gets a Wilson interval. Two variants on one fixture are two independent binomials,
compared with Fisher's exact test. A run usually compares many fixtures at once, and some will look
different by luck, so those chances are Holm-adjusted. A total across fixtures is not one big sample
(samples of one fixture are alike), so it is compared within each fixture and pooled with the
Cochran-Mantel-Haenszel test. Everything is plain arithmetic, so no statistics package is needed.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

Z95 = 1.959964
Z80 = 0.841621  # one-sided, for 80% power
ALPHA = 0.05


def wilson(passed: int, n: int, z: float = Z95) -> tuple[float, float]:
    """The 95% range the true pass rate probably sits in. (0, 1) when nothing was scored."""
    if n == 0:
        return 0.0, 1.0
    p = passed / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def fisher(a: int, n1: int, b: int, n2: int) -> float:
    """Two-sided chance of a gap at least this large if both had the same true rate."""
    if n1 == 0 or n2 == 0:
        return 1.0
    k, total = a + b, n1 + n2

    def prob(x: int) -> float:
        return math.comb(n1, x) * math.comb(n2, k - x) / math.comb(total, k)

    seen = prob(a)
    lo, hi = max(0, k - n2), min(k, n1)
    return min(1.0, sum(p for x in range(lo, hi + 1) if (p := prob(x)) <= seen * (1 + 1e-9)))


def holm(chances: Sequence[float]) -> list[float]:
    """Each chance adjusted for how many comparisons were made at once (Holm-Bonferroni)."""
    order = sorted(range(len(chances)), key=lambda i: chances[i])
    out = [1.0] * len(chances)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(chances) - rank) * chances[i]))
        out[i] = running
    return out


def cmh(strata: Sequence[tuple[int, int, int, int]]) -> float:
    """Chance the totals differ this much by luck, comparing within each fixture: each stratum is
    (passed under A, scored under A, passed under B, scored under B). Continuity-corrected."""
    gap = expected_var = 0.0
    for a, n1, b, n2 in strata:
        total, k = n1 + n2, a + b
        if n1 == 0 or n2 == 0 or total < 2:
            continue
        gap += a - n1 * k / total
        expected_var += n1 * n2 * k * (total - k) / (total * total * (total - 1))
    if expected_var == 0:
        return 1.0
    chi = (max(0.0, abs(gap) - 0.5)) ** 2 / expected_var
    return math.erfc(math.sqrt(chi / 2))


def samples_needed(p1: float, p2: float) -> int | None:
    """Samples per side to tell these two rates apart 80% of the time at the 5% line. None when
    they are equal."""
    if p1 == p2:
        return None
    mean = (p1 + p2) / 2
    top = Z95 * math.sqrt(2 * mean * (1 - mean)) + Z80 * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    return math.ceil((top / (p1 - p2)) ** 2)


@dataclass(frozen=True, slots=True)
class Comparison:
    label: str
    a: tuple[int, int]
    b: tuple[int, int]
    chance: float  # the chance of noise, adjusted when several were compared at once

    @property
    def real(self) -> bool:
        return self.chance < ALPHA

    def line(self) -> str:
        (pa, na), (pb, nb) = self.a, self.b
        verdict = "a real difference" if self.real else "within noise"
        text = (
            f"{self.label}: {pa}/{na} vs {pb}/{nb}, chance it is noise {self.chance:.0%}, {verdict}"
        )
        if not self.real and na and nb and (need := samples_needed(pa / na, pb / nb)):
            text += f" (about {need} samples each would tell a gap this size)"
        return text
