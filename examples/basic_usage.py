from boundevo import BoundEvo, BoundEvoConfig
from boundevo.benchmarks import make_box_problem

problem = make_box_problem("rastrigin", dimension=10)
optimizer = BoundEvo(
    BoundEvoConfig(
        population_size=100,
        parent_count=15,
        elite_parent_count=5,
        offspring_count=1,
        max_evaluations=50_000,
        seed=42,
    )
)
result = optimizer.minimize(problem)

print(f"f(x) = {result.objective:.8g}")
print(f"evaluations = {result.evaluations}")
print(f"generations = {result.generations}")
print(f"coefficient attempts = {result.coefficient_attempts}")
print(f"x = {result.x}")
