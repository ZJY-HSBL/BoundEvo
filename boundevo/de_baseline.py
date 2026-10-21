"""DE/rand/1/bin reference baseline for evaluation-budget-matched experiments.

This is a conventional, generational differential-evolution baseline. It is
not a new optimization algorithm, and it is not the BoundEvo optimizer.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .problem import OptimizationProblem, evaluation_key


@dataclass(frozen=True, slots=True)
class DEState:
    generation: int
    evaluations: int
    best_objective: float
    best_violation: float
    worst_objective: float
    worst_violation: float


@dataclass(frozen=True, slots=True)
class DEResult:
    x: np.ndarray
    objective: float
    violation: float
    evaluations: int
    generations: int
    history: tuple[DEState, ...]


def differential_evolution_rand1bin(
    problem: OptimizationProblem,
    *,
    seed: int,
    population_size: int = 100,
    max_evaluations: int = 10_000,
    mutation: float = 0.8,
    crossover: float = 0.9,
) -> DEResult:
    """Minimize using fully generational DE/rand/1/bin with hard FE accounting.

    Each generation constructs NP trial vectors from the *previous*
    population. For every target, three distinct random donor indices
    (none the target) form x_r1 + F*(x_r2 - x_r3). Binomial crossover
    always includes at least one donor coordinate; box violations are
    clipped; each trial competes only with its target.

    States are recorded after initialization and each complete generation,
    precisely every population_size objective evaluations.
    """

    if population_size < 4:
        raise ValueError("DE/rand/1/bin requires at least four individuals")
    if max_evaluations < population_size or max_evaluations % population_size != 0:
        raise ValueError("DE requires an integer number of full generations")
    if not np.isfinite(mutation) or not 0 < mutation <= 2.0:
        raise ValueError("DE mutation must be finite in (0,2]")
    if not np.isfinite(crossover) or not 0 <= crossover <= 1:
        raise ValueError("DE crossover must be finite in [0,1]")

    rng = np.random.default_rng(seed)
    pop = problem.sample_uniform(rng, population_size)
    current = [problem.evaluate(x) for x in pop]
    total = population_size
    states: list[DEState] = []

    def record(generation: int) -> None:
        best = min(current, key=evaluation_key)
        worst = max(current, key=evaluation_key)
        states.append(
            DEState(
                generation=generation,
                evaluations=total,
                best_objective=best.objective,
                best_violation=best.violation,
                worst_objective=worst.objective,
                worst_violation=worst.violation,
            )
        )

    record(0)
    total_generations = max_evaluations // population_size - 1
    for generation in range(1, total_generations + 1):
        next_pop = pop.copy()
        next_eval = current.copy()
        for target in range(population_size):
            # Draw three donor indices without replacement and excluding
            # target; the index shift maps [0, NP-2] into the allowed set.
            donors = rng.choice(population_size - 1, size=3, replace=False)
            donors += donors >= target
            a, b, c = (int(v) for v in donors)
            mutant = pop[a] + mutation * (pop[b] - pop[c])
            mask = rng.random(problem.dimension) < crossover
            mask[int(rng.integers(0, problem.dimension))] = True
            trial = problem.repair(np.where(mask, mutant, pop[target]))
            challenger = problem.evaluate(trial)
            total += 1
            if evaluation_key(challenger) <= evaluation_key(current[target]):
                next_pop[target] = challenger.x
                next_eval[target] = challenger
        pop = next_pop
        current = next_eval
        record(generation)

    if total != max_evaluations or len(states) != max_evaluations // population_size:
        raise RuntimeError("DE baseline failed the exact objective evaluation budget")
    best = min(current, key=evaluation_key)
    return DEResult(
        x=best.x.copy(),
        objective=best.objective,
        violation=best.violation,
        evaluations=total,
        generations=total_generations,
        history=tuple(states),
    )
