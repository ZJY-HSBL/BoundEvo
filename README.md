<div align="center">

# BoundEvo

**Adaptive Boundary Evolutionary Optimization**

A compact, reproducible Python implementation of real-coded multi-parent evolutionary optimization with adaptive-boundary coefficient generation.

[![CI](https://github.com/ZJY-HSBL/BoundEvo/actions/workflows/ci.yml/badge.svg)](https://github.com/ZJY-HSBL/BoundEvo/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![Version](https://img.shields.io/badge/version-0.3.0-2F6FEB)
![License](https://img.shields.io/badge/license-MIT-3DA639)

[中文说明](README_CN.md) · [Algorithm](docs/algorithm.md) · [Reproduction](docs/reproduction.md) · [Parent Sweep](docs/parent_sweep.md) · [v0.3.0 Notes](docs/releases/v0.3.0.md)

</div>

## Overview

BoundEvo focuses on a bottleneck in multi-parent affine recombination: efficiently generating coefficient vectors satisfying

    sum(alpha) = 1
    -0.5 <= alpha_i <= 1.5

The adaptive-boundary generator uses the running coefficient sum to determine the next feasible interval. After generating the first M-1 coefficients, the final coefficient is fixed by the sum constraint. This avoids rejection sampling for the adaptive-boundary method.

The repository keeps three coefficient generators under the same evolutionary engine:

| Method | Generator | Role |
|:---|:---|:---|
| RE | random exhaustive / rejection sampling | EP-GTA-style baseline |
| EDBF | empirical-distribution sampling | improved baseline |
| ABC | adaptive-boundary constraint | BoundEvo default |

## What is included

| Layer | Capability |
|:---|:---|
| Core | Elite preservation, multi-parent affine recombination, bounded-domain repair |
| Coefficients | RE, EDBF, ABC |
| Benchmarks | Sphere, Rosenbrock, Rastrigin, Ackley, CEC2017 |
| Main experiment | 29 CEC2017 functions: F1 and F3-F30 |
| Parent-count study | M=10..16 on F1, F10, F20, F30 |
| Efficiency study | M=1..20 coefficient-generation efficiency |
| Statistics | Mean rank, Win/Tie/Loss, Wilcoxon + Holm, Friedman |
| Outputs | CSV, Markdown tables, PNG plots |
| Validation | Python 3.10/3.11/3.12 CI and CEC2017 smoke tests |

## Installation

Core package:

~~~bash
git clone https://github.com/ZJY-HSBL/BoundEvo.git
cd BoundEvo
pip install -e .
~~~

Full experiment environment:

~~~bash
pip install -e ".[cec2017,analysis,plot]"
~~~

Development:

~~~bash
pip install -e ".[dev]"
ruff check .
pytest
~~~

## Unified CLI

Version 0.3 provides one command for the complete experiment workflow.

~~~bash
boundevo --version
boundevo benchmark --config configs/cec2017.json
boundevo sweep --config configs/parent_sweep.json
boundevo efficiency --config configs/efficiency.json
boundevo analyze --config configs/analysis.json
~~~

The JSON files under <code>configs/</code> are reproducible presets. Command-line overrides are available for common runtime parameters such as dimension, repeats, evaluation budget, seed, and output paths.

## Quick Python usage

~~~python
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
~~~

## Reproduction matrix

The source-aligned main configuration is:

    N = 100
    M = 15
    K = 5
    L = 1

The parent-count study varies <code>M=10..16</code> on F1, F10, F20, and F30 while keeping N=100, K=5, and L=1.

The extracted experiment-setting text does not state benchmark dimensionality. BoundEvo therefore keeps dimension explicit. The supplied presets use dimension 10 as a runnable default, not as a claim about the source experiment.

## Statistical analysis

After producing <code>results/cec2017_summary.csv</code>:

~~~bash
boundevo analyze --config configs/analysis.json
~~~

The generated Markdown report contains:

- average ranks across complete benchmark cases;
- Win/Tie/Loss counts against the selected reference method;
- two-sided paired Wilcoxon signed-rank tests;
- Holm-adjusted pairwise p-values;
- a Friedman omnibus test across all selected methods.

The default metric is <code>mean_error</code>, with lower values treated as better.

## Implementation notes

The source ABC flowchart contains an indexing ambiguity around the final coefficient. A literal reading would leave one coefficient undefined. BoundEvo uses the mathematically consistent M-dimensional interpretation: generate M-1 coefficients under adaptive bounds, then compute the M-th coefficient from the sum constraint.

When affine recombination leaves the variable box, offspring are projected back into the domain. This is an explicit implementation choice and is documented rather than silently treated as part of the source method.

## Repository structure

    boundevo/       optimizer, coefficient generators, CEC2017 adapter, statistics, CLI
    configs/        reproducible JSON experiment presets
    docs/           algorithm and reproduction notes
    examples/       Python usage examples
    scripts/        plotting and standalone experiment utilities
    tests/          unit and integration tests
    .github/        CI workflow

## Release

The v0.3.0 release notes are prepared in [docs/releases/v0.3.0.md](docs/releases/v0.3.0.md). Full changes are recorded in [CHANGELOG.md](CHANGELOG.md).

## License

MIT License.
