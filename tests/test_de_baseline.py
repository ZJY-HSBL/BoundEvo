from itertools import pairwise

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


def test_de_best1bin_preserves_matched_initialization_and_reproducibility() -> None:
    problem = OptimizationProblem(sphere, [-10.0] * 4, [10.0] * 4)
    cfg = {"strategy": "best1bin", "population_size": 20, "max_evaluations": 400, "seed": 73}
    first = differential_evolution_rand1bin(problem, **cfg)
    second = differential_evolution_rand1bin(problem, **cfg)
    plain = differential_evolution_rand1bin(
        problem, strategy="rand1bin", population_size=20,
        max_evaluations=400, seed=73
    )
    assert first.history == second.history
    assert first.history[0] == plain.history[0]
    assert first.evaluations == plain.evaluations == 400
    assert first.history[-1].best_objective == first.objective
    assert first.objective <= first.history[0].best_objective


def test_jde_exact_budget_and_reproducible_adaptation() -> None:
    from boundevo.de_baseline import differential_evolution_jde

    problem = OptimizationProblem(sphere, [-9.] * 5, [9.] * 5)
    first = differential_evolution_jde(
        problem, population_size=25, max_evaluations=500, seed=191
    )
    second = differential_evolution_jde(
        problem, population_size=25, max_evaluations=500, seed=191
    )
    standard = differential_evolution_rand1bin(
        problem, population_size=25, max_evaluations=500, seed=191
    )
    assert first.evaluations == 500
    assert [r.evaluations for r in first.history] == list(range(25, 501, 25))
    assert first.history == second.history
    assert first.history[0] == standard.history[0]
    assert first.objective <= first.history[0].best_objective
    assert all(
        a.best_objective >= b.best_objective
        for a, b in pairwise(first.history)
    )


@pytest.mark.parametrize("params", [
    {"population_size": 3}, {"max_evaluations": 199},
    {"initial_mutation": -1}, {"initial_crossover": 2},
    {"tau_f": float("nan")}, {"tau_cr": -1},
])
def test_jde_invalid_configuration(params: dict) -> None:
    from boundevo.de_baseline import differential_evolution_jde

    problem = OptimizationProblem(sphere, [-3] * 4, [3] * 4)
    with pytest.raises(ValueError):
        differential_evolution_jde(problem, seed=37, **params)
