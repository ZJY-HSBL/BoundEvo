"""Check DE/rand/1/bin scientific and reproducibility contracts."""

import numpy as np
import pytest

from boundevo import BoundEvo, BoundEvoConfig, OptimizationProblem
from boundevo.de_baseline import differential_evolution_rand1bin


def sphere(x: np.ndarray) -> float:
    return float(np.dot(x, x))


def test_de_exact_budget_and_real_monotone_history() -> None:
    problem = OptimizationProblem(sphere, [-4.0] * 5, [4.0] * 5)
    result = differential_evolution_rand1bin(
        problem, population_size=20, max_evaluations=400, seed=1729
    )
    assert result.evaluations == 400
    assert result.generations == 19
    assert [s.evaluations for s in result.history] == list(range(20, 401, 20))
    assert all(
        right.best_objective <= left.best_objective
        for left, right in zip(result.history, result.history[1:])
    )
    assert result.objective == pytest.approx(result.history[-1].best_objective)
    assert result.objective < result.history[0].best_objective
    assert np.all(result.x <= problem.upper)
    assert np.all(result.x >= problem.lower)


def test_de_reproducible_and_initialization_matched_to_abc() -> None:
    problem = OptimizationProblem(sphere, [-10.0] * 6, [10.0] * 6)
    first = differential_evolution_rand1bin(
        problem, population_size=30, max_evaluations=120, seed=53
    )
    second = differential_evolution_rand1bin(
        problem, population_size=30, max_evaluations=120, seed=53
    )
    np.testing.assert_array_equal(first.x, second.x)
    assert first.objective == second.objective
    assert first.history == second.history
    abc = BoundEvo(
        BoundEvoConfig(
            population_size=30,
            parent_count=10,
            elite_parent_count=3,
            max_evaluations=120,
            seed=53,
        )
    ).minimize(problem, history_interval=1)
    assert abc.history[0].best_objective == first.history[0].best_objective


def test_de_enforces_binomial_crossover_and_domain() -> None:
    # A zero-crossover control must still force at least one donor coordinate.
    # A flat bounded domain avoids any assumption about expected objective.
    observed = []
    def objective(point: np.ndarray) -> float:
        observed.append(point.copy())
        return float(np.sum(point * point))

    problem = OptimizationProblem(objective, [-1.0] * 3, [1.0] * 3)
    result = differential_evolution_rand1bin(
        problem, seed=8, population_size=8, max_evaluations=40, crossover=0.0
    )
    assert len(observed) == result.evaluations == 40
    assert all(np.all(point <= 1) and np.all(point >= -1) for point in observed)
    assert all(a.best_objective >= b.best_objective for a, b in
               zip(result.history, result.history[1:]))


@pytest.mark.parametrize("kwargs", [
    {"population_size": 3}, {"population_size": 10, "max_evaluations": 99},
    {"mutation": -1.0}, {"mutation": float("inf")}, {"crossover": 1.4},
])
def test_de_rejects_invalid_configuration(kwargs: dict) -> None:
    problem = OptimizationProblem(sphere, [-1] * 3, [1] * 3)
    with pytest.raises(ValueError):
        differential_evolution_rand1bin(problem, seed=1, **kwargs)
