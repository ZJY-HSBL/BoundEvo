import numpy as np

from boundevo import BoundEvo, BoundEvoConfig, OptimizationProblem


def test_optimizer_improves_sphere() -> None:
    problem = OptimizationProblem(
        lambda x: float(np.dot(x, x)),
        np.full(5, -10.0),
        np.full(5, 10.0),
    )
    optimizer = BoundEvo(
        BoundEvoConfig(
            population_size=40,
            parent_count=10,
            elite_parent_count=4,
            offspring_count=2,
            max_evaluations=2500,
            seed=123,
        )
    )
    result = optimizer.minimize(problem)
    initial_best = result.history[0].best_objective
    assert result.objective <= initial_best
    assert result.objective < 1e-2
    assert result.violation == 0.0
    assert result.evaluations <= 2500


def test_constrained_problem_finds_feasible_solution() -> None:
    # Minimize x^2 but require x >= 1.  Constrained optimum is x=1.
    problem = OptimizationProblem(
        lambda x: float(x[0] ** 2),
        [-5.0],
        [5.0],
        constraints=[lambda x: float(1.0 - x[0])],
    )
    result = BoundEvo(
        BoundEvoConfig(
            population_size=30,
            parent_count=8,
            elite_parent_count=3,
            max_evaluations=2000,
            seed=9,
        )
    ).minimize(problem)
    assert result.violation <= 1e-10
    assert result.x[0] >= 1.0 - 1e-8
    assert result.objective < 1.2
