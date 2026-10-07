"""Elite multi-parent evolutionary optimizer using BoundEvo coefficients."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

import numpy as np

from .coefficients import Method, generate_coefficients
from .problem import Evaluation, OptimizationProblem, evaluation_key

Array = np.ndarray
Callback = Callable[["OptimizationState"], None]


@dataclass(frozen=True, slots=True)
class BoundEvoConfig:
    population_size: int = 100
    parent_count: int = 15
    elite_parent_count: int = 5
    offspring_count: int = 1
    max_evaluations: int = 100_000
    coefficient_method: Method = "abc"
    seed: int | None = None
    convergence_atol: float = 1e-12

    def validate(self) -> None:
        if self.population_size < 2:
            raise ValueError("population_size must be at least 2")
        if not 1 <= self.parent_count <= self.population_size:
            raise ValueError("parent_count must be in [1, population_size]")
        if not 0 <= self.elite_parent_count <= self.parent_count:
            raise ValueError("elite_parent_count must be in [0, parent_count]")
        if self.offspring_count < 1:
            raise ValueError("offspring_count must be at least 1")
        if self.max_evaluations < self.population_size:
            raise ValueError("max_evaluations must cover the initial population")
        if self.convergence_atol < 0:
            raise ValueError("convergence_atol must be non-negative")


@dataclass(frozen=True, slots=True)
class OptimizationState:
    generation: int
    evaluations: int
    best_objective: float
    best_violation: float
    worst_objective: float
    worst_violation: float


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    x: Array
    objective: float
    violation: float
    evaluations: int
    generations: int
    converged: bool
    coefficient_attempts: int
    history: tuple[OptimizationState, ...]


class BoundEvo:
    """Real-coded multi-parent optimizer with elite preservation.

    Each generation keeps K best parents, adds M-K uniformly sampled parents
    from the remainder of the population, creates L affine-combination children,
    and replaces the current worst individual when the best child is better.
    """

    def __init__(self, config: BoundEvoConfig | None = None) -> None:
        self.config = config or BoundEvoConfig()
        self.config.validate()

    def minimize(
        self,
        problem: OptimizationProblem,
        *,
        callback: Callback | None = None,
    ) -> OptimizationResult:
        cfg = self.config
        rng = np.random.default_rng(cfg.seed)

        population = problem.sample_uniform(rng, cfg.population_size)
        evaluated = [problem.evaluate(x) for x in population]
        evaluations = cfg.population_size
        generation = 0
        coefficient_attempts = 0
        history: list[OptimizationState] = []

        while True:
            order = sorted(range(len(evaluated)), key=lambda i: evaluation_key(evaluated[i]))
            population = population[order]
            evaluated = [evaluated[i] for i in order]

            best = evaluated[0]
            worst = evaluated[-1]
            state = OptimizationState(
                generation=generation,
                evaluations=evaluations,
                best_objective=best.objective,
                best_violation=best.violation,
                worst_objective=worst.objective,
                worst_violation=worst.violation,
            )
            history.append(state)
            if callback is not None:
                callback(state)

            converged = self._population_converged(best, worst, cfg.convergence_atol)
            if converged or evaluations >= cfg.max_evaluations:
                return OptimizationResult(
                    x=best.x.copy(),
                    objective=best.objective,
                    violation=best.violation,
                    evaluations=evaluations,
                    generations=generation,
                    converged=converged,
                    coefficient_attempts=coefficient_attempts,
                    history=tuple(history),
                )

            parent_indices = self._select_parent_indices(rng)
            parents = population[parent_indices]

            children: list[Evaluation] = []
            remaining_budget = cfg.max_evaluations - evaluations
            child_count = min(cfg.offspring_count, remaining_budget)
            for _ in range(child_count):
                generated = generate_coefficients(
                    cfg.parent_count,
                    method=cfg.coefficient_method,
                    rng=rng,
                )
                coefficient_attempts += generated.attempts
                child = generated.coefficients @ parents
                child = problem.repair(child)
                children.append(problem.evaluate(child))
                evaluations += 1

            if not children:
                continue

            child_best = min(children, key=evaluation_key)
            if evaluation_key(child_best) <= evaluation_key(worst):
                population[-1] = child_best.x
                evaluated[-1] = child_best

            generation += 1

    def _select_parent_indices(self, rng: np.random.Generator) -> Array:
        cfg = self.config
        k = cfg.elite_parent_count
        elite = np.arange(k, dtype=np.int64)
        random_count = cfg.parent_count - k
        if random_count == 0:
            return elite
        pool = np.arange(k, cfg.population_size, dtype=np.int64)
        random_part = rng.choice(pool, size=random_count, replace=False)
        return np.concatenate((elite, random_part))

    @staticmethod
    def _population_converged(best: Evaluation, worst: Evaluation, atol: float) -> bool:
        return bool(
            np.isclose(best.violation, worst.violation, atol=atol, rtol=0.0)
            and np.isclose(best.objective, worst.objective, atol=atol, rtol=0.0)
        )
