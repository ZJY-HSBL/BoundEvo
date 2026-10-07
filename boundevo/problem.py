"""Problem definition and feasibility-aware comparison utilities."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable, Iterable

import numpy as np

Array = np.ndarray
Objective = Callable[[Array], float]
Constraint = Callable[[Array], float]


@dataclass(frozen=True, slots=True)
class Evaluation:
    x: Array
    objective: float
    violation: float


@dataclass(frozen=True, slots=True)
class OptimizationProblem:
    """Bound-constrained minimization problem with optional g(x) <= 0 constraints."""

    objective: Objective
    lower: Array
    upper: Array
    constraints: tuple[Constraint, ...] = ()

    def __init__(
        self,
        objective: Objective,
        lower: Array | Iterable[float],
        upper: Array | Iterable[float],
        constraints: Iterable[Constraint] = (),
    ) -> None:
        lo = np.asarray(lower, dtype=np.float64)
        hi = np.asarray(upper, dtype=np.float64)
        if lo.ndim != 1 or hi.ndim != 1 or lo.shape != hi.shape or lo.size == 0:
            raise ValueError("lower and upper must be non-empty one-dimensional arrays of equal length")
        if np.any(lo >= hi):
            raise ValueError("each lower bound must be strictly smaller than its upper bound")
        object.__setattr__(self, "objective", objective)
        object.__setattr__(self, "lower", lo)
        object.__setattr__(self, "upper", hi)
        object.__setattr__(self, "constraints", tuple(constraints))

    @property
    def dimension(self) -> int:
        return int(self.lower.size)

    def evaluate(self, x: Array) -> Evaluation:
        point = np.asarray(x, dtype=np.float64)
        if point.shape != self.lower.shape:
            raise ValueError(f"expected shape {self.lower.shape}, got {point.shape}")
        objective = float(self.objective(point))
        violation = float(sum(max(0.0, float(g(point))) for g in self.constraints))
        if not np.isfinite(objective) or not np.isfinite(violation):
            raise ValueError("objective and constraint values must be finite")
        return Evaluation(point.copy(), objective, violation)

    def sample_uniform(self, rng: np.random.Generator, count: int) -> Array:
        if count < 1:
            raise ValueError("count must be at least 1")
        return rng.uniform(self.lower, self.upper, size=(count, self.dimension))

    def repair(self, x: Array) -> Array:
        """Project offspring back into the box domain D."""

        return np.clip(np.asarray(x, dtype=np.float64), self.lower, self.upper)


def evaluation_key(evaluation: Evaluation) -> tuple[float, float]:
    """Feasibility first; objective value breaks equal-violation ties."""

    return evaluation.violation, evaluation.objective


def better(left: Evaluation, right: Evaluation) -> bool:
    """Return whether *left* is no worse than *right* under the paper's ordering."""

    return evaluation_key(left) <= evaluation_key(right)
