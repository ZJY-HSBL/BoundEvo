import numpy as np

from boundevo import BoundEvo, BoundEvoConfig, OptimizationProblem

# min (x0-1)^2 + (x1-2)^2
# s.t. x0 + x1 >= 2.5, represented as g(x) = 2.5-x0-x1 <= 0
problem = OptimizationProblem(
    objective=lambda x: float((x[0] - 1.0) ** 2 + (x[1] - 2.0) ** 2),
    lower=np.array([-5.0, -5.0]),
    upper=np.array([5.0, 5.0]),
    constraints=[lambda x: float(2.5 - x[0] - x[1])],
)

result = BoundEvo(BoundEvoConfig(seed=7, max_evaluations=20_000)).minimize(problem)
print("x:", result.x)
print("objective:", result.objective)
print("constraint violation:", result.violation)
