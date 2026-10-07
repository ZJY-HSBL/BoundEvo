"""Coefficient-vector generators for multi-parent recombination.

A valid coefficient vector ``alpha`` satisfies

    sum(alpha) = 1
    -0.5 <= alpha[i] <= 1.5

The adaptive generator is the core of BoundEvo.  It chooses the first M-1
coefficients sequentially while constraining the running sum to [-0.5, 1.5].
Consequently the final coefficient, 1 - sum(alpha[:-1]), is guaranteed to lie
in [-0.5, 1.5] and no rejection loop is required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

Array = np.ndarray
Method = Literal["abc", "re", "edbf"]


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """A coefficient vector together with the number of full-vector attempts."""

    coefficients: Array
    attempts: int = 1


def _validate_parent_count(parent_count: int) -> None:
    if parent_count < 1:
        raise ValueError("parent_count must be at least 1")


def _finish(prefix: list[float]) -> Array:
    final = 1.0 - float(np.sum(prefix, dtype=np.float64))
    return np.asarray([*prefix, final], dtype=np.float64)


def is_valid_coefficients(coefficients: Array, *, atol: float = 1e-12) -> bool:
    """Return whether a vector satisfies the recombination constraints."""

    alpha = np.asarray(coefficients, dtype=np.float64)
    return bool(
        alpha.ndim == 1
        and alpha.size >= 1
        and np.all(alpha >= -0.5 - atol)
        and np.all(alpha <= 1.5 + atol)
        and np.isclose(alpha.sum(), 1.0, atol=atol, rtol=0.0)
    )


def adaptive_boundary_coefficients(
    parent_count: int,
    rng: np.random.Generator | None = None,
) -> GenerationResult:
    """Generate a valid vector using adaptive boundary constraints (ABC).

    Let ``s`` be the sum of already generated coefficients.  For the next
    coefficient, BoundEvo samples uniformly from

        [max(-0.5 - s, -0.5), min(1.5 - s, 1.5)].

    This keeps the updated running sum inside [-0.5, 1.5].  After M-1 random
    coefficients, the final value ``1-s`` is therefore guaranteed to be valid.
    """

    _validate_parent_count(parent_count)
    if parent_count == 1:
        return GenerationResult(np.asarray([1.0], dtype=np.float64), 1)

    rng = rng or np.random.default_rng()
    prefix: list[float] = []
    running_sum = 0.0

    for _ in range(parent_count - 1):
        lower = max(-0.5 - running_sum, -0.5)
        upper = min(1.5 - running_sum, 1.5)
        # Floating-point roundoff can produce a tiny reversed interval only at
        # the mathematical boundary. Collapse that interval instead of failing.
        if lower > upper and np.isclose(lower, upper, atol=1e-15, rtol=0.0):
            lower = upper = 0.5 * (lower + upper)
        value = float(rng.uniform(lower, upper)) if lower < upper else float(lower)
        prefix.append(value)
        running_sum += value

    coefficients = _finish(prefix)
    if not is_valid_coefficients(coefficients, atol=2e-12):
        raise RuntimeError("ABC generator produced an invalid coefficient vector")
    return GenerationResult(coefficients, 1)


def random_exhaustive_coefficients(
    parent_count: int,
    rng: np.random.Generator | None = None,
    *,
    max_attempts: int = 1_000_000,
) -> GenerationResult:
    """Generate a vector by the rejection-based random exhaustive (RE) method."""

    _validate_parent_count(parent_count)
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if parent_count == 1:
        return GenerationResult(np.asarray([1.0], dtype=np.float64), 1)

    rng = rng or np.random.default_rng()
    for attempt in range(1, max_attempts + 1):
        prefix = rng.uniform(-0.5, 1.5, size=parent_count - 1)
        coefficients = _finish(prefix.tolist())
        if -0.5 <= coefficients[-1] <= 1.5:
            return GenerationResult(coefficients, attempt)

    raise RuntimeError(f"RE failed to generate a valid vector in {max_attempts} attempts")


def edbf_probabilities(parent_count: int) -> tuple[float, float, float]:
    """Return EDBF interval probabilities for [-.5,0], [0,1], and [1,1.5]."""

    _validate_parent_count(parent_count)
    m = float(parent_count)
    p1 = -0.85286 * m ** (-0.9424) + 0.6115
    p2 = -0.5802 * m ** (-0.8598) + 0.3442
    p3 = 1.0 - p1 - p2
    probs = np.asarray([p1, p2, p3], dtype=np.float64)
    if np.any(probs < 0.0) or not np.isclose(probs.sum(), 1.0):
        raise RuntimeError(f"invalid EDBF probabilities for M={parent_count}: {probs}")
    return float(p1), float(p2), float(p3)


def _sample_edbf_value(parent_count: int, rng: np.random.Generator) -> float:
    p1, p2, _ = edbf_probabilities(parent_count)
    r = float(rng.random())
    if r <= p1:
        return float(rng.uniform(-0.5, 0.0))
    if r <= p1 + p2:
        return float(rng.uniform(0.0, 1.0))
    return float(rng.uniform(1.0, 1.5))


def edbf_coefficients(
    parent_count: int,
    rng: np.random.Generator | None = None,
    *,
    max_attempts: int = 1_000_000,
) -> GenerationResult:
    """Generate a vector using the empirical-distribution-based framework."""

    _validate_parent_count(parent_count)
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if parent_count == 1:
        return GenerationResult(np.asarray([1.0], dtype=np.float64), 1)

    rng = rng or np.random.default_rng()
    for attempt in range(1, max_attempts + 1):
        prefix = [_sample_edbf_value(parent_count, rng) for _ in range(parent_count - 1)]
        coefficients = _finish(prefix)
        if -0.5 <= coefficients[-1] <= 1.5:
            return GenerationResult(coefficients, attempt)

    raise RuntimeError(f"EDBF failed to generate a valid vector in {max_attempts} attempts")


def generate_coefficients(
    parent_count: int,
    *,
    method: Method = "abc",
    rng: np.random.Generator | None = None,
    max_attempts: int = 1_000_000,
) -> GenerationResult:
    """Dispatch to one of the supported coefficient-vector generators."""

    if method == "abc":
        return adaptive_boundary_coefficients(parent_count, rng)
    if method == "re":
        return random_exhaustive_coefficients(parent_count, rng, max_attempts=max_attempts)
    if method == "edbf":
        return edbf_coefficients(parent_count, rng, max_attempts=max_attempts)
    raise ValueError(f"unknown coefficient generation method: {method!r}")
