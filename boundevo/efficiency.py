"""Coefficient-vector generation efficiency estimators.

The efficiency metric is the fraction of independently proposed coefficient
vectors that satisfy the final coefficient bound. ABC is exact and therefore
has efficiency 1 for every valid parent count.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .coefficients import edbf_probabilities


@dataclass(frozen=True, slots=True)
class EfficiencyPoint:
    parent_count: int
    method: str
    trials: int
    accepted: int
    efficiency: float


def _validate(parent_count: int, trials: int, batch_size: int) -> None:
    if parent_count < 1:
        raise ValueError("parent_count must be at least 1")
    if trials < 1:
        raise ValueError("trials must be at least 1")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")


def _re_prefix_sums(
    rng: np.random.Generator,
    rows: int,
    parent_count: int,
) -> np.ndarray:
    if parent_count == 1:
        return np.zeros(rows, dtype=np.float64)
    return rng.uniform(-0.5, 1.5, size=(rows, parent_count - 1)).sum(axis=1)


def _edbf_prefix_sums(
    rng: np.random.Generator,
    rows: int,
    parent_count: int,
) -> np.ndarray:
    if parent_count == 1:
        return np.zeros(rows, dtype=np.float64)
    p1, p2, _ = edbf_probabilities(parent_count)
    choices = rng.random(size=(rows, parent_count - 1))
    values = np.empty_like(choices)
    negative = choices <= p1
    middle = (choices > p1) & (choices <= p1 + p2)
    positive = ~(negative | middle)
    values[negative] = rng.uniform(-0.5, 0.0, size=int(negative.sum()))
    values[middle] = rng.uniform(0.0, 1.0, size=int(middle.sum()))
    values[positive] = rng.uniform(1.0, 1.5, size=int(positive.sum()))
    return values.sum(axis=1)


def estimate_efficiency(
    parent_count: int,
    *,
    method: str,
    trials: int = 1_000_000,
    seed: int = 42,
    batch_size: int = 100_000,
) -> EfficiencyPoint:
    """Estimate RE/EDBF efficiency or return the exact ABC value."""

    _validate(parent_count, trials, batch_size)
    if method == "abc":
        return EfficiencyPoint(parent_count, method, trials, trials, 1.0)
    if method not in {"re", "edbf"}:
        raise ValueError(f"unknown method: {method!r}")
    if parent_count == 1:
        return EfficiencyPoint(parent_count, method, trials, trials, 1.0)

    rng = np.random.default_rng(seed)
    accepted = 0
    remaining = trials
    while remaining:
        rows = min(batch_size, remaining)
        if method == "re":
            prefix = _re_prefix_sums(rng, rows, parent_count)
        else:
            prefix = _edbf_prefix_sums(rng, rows, parent_count)
        final = 1.0 - prefix
        accepted += int(np.count_nonzero((final >= -0.5) & (final <= 1.5)))
        remaining -= rows

    return EfficiencyPoint(
        parent_count=parent_count,
        method=method,
        trials=trials,
        accepted=accepted,
        efficiency=accepted / trials,
    )
