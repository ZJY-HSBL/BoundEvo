<div align="center">

# BoundEvo

**Adaptive Boundary Evolutionary Optimization**

A compact, reproducible Python implementation of real-coded multi-parent evolutionary optimization with adaptive-boundary coefficient generation.

[![CI](https://github.com/ZJY-HSBL/BoundEvo/actions/workflows/ci.yml/badge.svg)](https://github.com/ZJY-HSBL/BoundEvo/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![Release](https://img.shields.io/badge/release-v0.4.0-2F6FEB)
![License](https://img.shields.io/badge/license-MIT-3DA639)

[中文说明](README_CN.md) · [Algorithm](docs/algorithm.md) · [Reproduction](docs/reproduction.md) · [Research Workflow](docs/research_workflow.md) · [v0.4.0 Notes](docs/releases/v0.4.0.md)

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
| Reproducibility | JSON run manifests with resolved configuration and environment |
| Reporting | CSV, Markdown tables, PNG plots, standalone HTML report |
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

The command-line interface covers the complete experiment-to-report workflow.

~~~bash
boundevo --version
boundevo benchmark --config configs/cec2017.json
boundevo sweep --config configs/parent_sweep.json
boundevo efficiency --config configs/efficiency.json
boundevo analyze --config configs/analysis.json
boundevo report --config configs/report.json
boundevo pipeline --config configs/pipeline.json
~~~

The JSON files under <code>configs/</code> are reproducible presets. Command-line overrides are available for common runtime parameters such as dimension, repeats, evaluation budget, seed, and output paths.

For a complete managed run, use <code>boundevo pipeline</code>. It generates a unique Run ID and stores the benchmark, parent-count sweep, efficiency study, statistics, manifests, and final HTML report under one non-overwriting directory:

    results/runs/<run-id>/
    ├── benchmark/
    ├── sweep/
    ├── efficiency/
    ├── analysis/
    ├── report/
    └── manifest.json

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

The generated Markdown report contains average ranks, Win/Tie/Loss counts, two-sided paired Wilcoxon signed-rank tests, Holm-adjusted p-values, and a Friedman omnibus test. The default metric is <code>mean_error</code>, with lower values treated as better.

## Reproducibility manifests and HTML report

Every main CLI stage writes a JSON manifest by default. A manifest records the fully resolved configuration, BoundEvo version, Python runtime, operating platform, relevant dependency versions, source revision when available, and output file locations.

After the experiments and analysis finish:

~~~bash
boundevo report --config configs/report.json
~~~

This creates <code>results/report.html</code>, a self-contained report that can be opened directly in a browser without a Python environment. The report now includes inline SVG convergence curves from sampled optimizer history, M-sensitivity curves from the parent-count sweep, and the coefficient-generation efficiency curve. No JavaScript or plotting runtime is required to view the report.

For long runs, <code>history_interval</code> controls history sampling. The default value of 100 keeps the final state while avoiding one CSV row per generation. The complete pipeline is documented in [docs/research_workflow.md](docs/research_workflow.md).

## Implementation notes

The source ABC flowchart contains an indexing ambiguity around the final coefficient. A literal reading would leave one coefficient undefined. BoundEvo uses the mathematically consistent M-dimensional interpretation: generate M-1 coefficients under adaptive bounds, then compute the M-th coefficient from the sum constraint.

When affine recombination leaves the variable box, offspring are projected back into the domain. This is an explicit implementation choice and is documented rather than silently treated as part of the source method.

## Repository structure

    boundevo/       optimizer, generators, CEC2017, statistics, manifests, reporting, CLI
    configs/        reproducible JSON experiment presets
    docs/           algorithm, reproduction, workflow, and release notes
    examples/       Python usage examples
    scripts/        plotting and standalone experiment utilities
    tests/          unit and integration tests
    .github/        CI and release workflows

## Release

[v0.4.0](https://github.com/ZJY-HSBL/BoundEvo/releases/tag/v0.4.0) is the current published release. See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

MIT License.
