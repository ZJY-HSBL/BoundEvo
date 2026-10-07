import numpy as np

from boundevo.problem import OptimizationProblem, better


def test_feasibility_precedes_objective() -> None:
    problem = OptimizationProblem(
        lambda x: float(x[0]),
        [-10.0],
        [10.0],
        constraints=[lambda x: float(1.0 - x[0])],
    )
    infeasible_low_objective = problem.evaluate(np.array([0.0]))
    feasible_high_objective = problem.evaluate(np.array([2.0]))
    assert better(feasible_high_objective, infeasible_low_objective)


def test_repair_clips_to_domain() -> None:
    problem = OptimizationProblem(lambda x: float(np.dot(x, x)), [-1.0, -2.0], [1.0, 2.0])
    np.testing.assert_allclose(problem.repair(np.array([-3.0, 4.0])), [-1.0, 2.0])
