# BoundEvo

**Adaptive Boundary Evolutionary Optimization** — a compact Python implementation of an elite-preserving, real-coded multi-parent genetic optimizer with efficient adaptive-boundary coefficient generation.

[中文说明](README_CN.md)

## Why BoundEvo

For multi-parent affine recombination, coefficients must satisfy

```text
sum(alpha) = 1
-0.5 <= alpha_i <= 1.5
```

Naive random generation increasingly wastes samples as the number of parents grows. BoundEvo's adaptive-boundary generator uses the running coefficient sum to shrink or expand the next sampling interval, so every generated vector is valid in a single attempt.

The repository also includes RE and EDBF generators for direct comparison.

## Core idea

With running sum `s`, the next coefficient is sampled from

```text
lower = max(-0.5 - s, -0.5)
upper = min( 1.5 - s,  1.5)
alpha_i ~ Uniform(lower, upper)
```

After the first `M-1` values are generated, the last coefficient is

```text
alpha_M = 1 - s
```

The adaptive interval keeps `s` inside `[-0.5, 1.5]`, therefore the final coefficient is automatically valid.

## Installation

```bash
git clone https://github.com/ZJY-HSBL/BoundEvo.git
cd BoundEvo
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
pytest
```

## Quick start

```python
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
print(result.objective)
print(result.x)
```

The default `N=100, M=15, K=5, L=1` configuration follows the main experimental setting described in the source material.

## Constrained optimization

Inequality constraints use the form `g(x) <= 0`. Candidates are ranked first by total positive constraint violation and then by objective value.

```python
import numpy as np
from boundevo import BoundEvo, OptimizationProblem

problem = OptimizationProblem(
    objective=lambda x: float(x[0] ** 2),
    lower=np.array([-5.0]),
    upper=np.array([5.0]),
    constraints=[lambda x: float(1.0 - x[0])],  # x >= 1
)

result = BoundEvo().minimize(problem)
```

## Coefficient generators

```python
import numpy as np
from boundevo import generate_coefficients

rng = np.random.default_rng(42)
for method in ("re", "edbf", "abc"):
    result = generate_coefficients(15, method=method, rng=rng)
    print(method, result.attempts, result.coefficients.sum())
```

Run the generator benchmark with:

```bash
python scripts/benchmark_generators.py --min-m 2 --max-m 20 --repeats 10000
```

## Implementation notes

The published ABC flowchart contains an indexing ambiguity: its decision node is printed around `i == M-1`, while the next box directly computes `alpha_M = 1-s`. A literal reading would leave one coefficient undefined. BoundEvo uses the mathematically consistent interpretation required by the stated M-dimensional coefficient vector: generate `M-1` coefficients, then compute the M-th from the sum constraint. See [`docs/algorithm.md`](docs/algorithm.md).

Offspring are projected back into the variable bounds when an affine recombination leaves the search box. This repair rule is an explicit implementation choice.

## Project layout

```text
boundevo/       Core optimizer, coefficient generators, benchmark functions
examples/       Unconstrained and constrained usage examples
scripts/        Coefficient-generation benchmark
 tests/         Unit and integration tests
 docs/          Algorithm notes and reproduction decisions
```

## License

MIT License.
