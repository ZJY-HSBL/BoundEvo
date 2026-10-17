# Research workflow

BoundEvo separates optimization, experiment execution, statistical analysis, and
reporting, while the managed pipeline can execute those stages under one unique
Run ID.

## Recommended: one managed run

Install the full experiment environment:

~~~bash
pip install -e ".[cec2017,analysis,plot]"
~~~

Then run:

~~~bash
boundevo pipeline --config configs/pipeline.json
~~~

A new non-overwriting directory is created automatically:

~~~text
results/runs/experiment-YYYYMMDDTHHMMSSZ-xxxxxxxx/
├── benchmark/
│   ├── trials.csv
│   ├── summary.csv
│   ├── history.csv
│   └── manifest.json
├── sweep/
│   ├── trials.csv
│   ├── summary.csv
│   ├── history.csv
│   ├── tables.md
│   └── manifest.json
├── efficiency/
│   ├── efficiency.csv
│   └── manifest.json
├── analysis/
│   ├── statistical_analysis.md
│   └── manifest.json
├── report/
│   ├── report.html
│   └── manifest.json
└── manifest.json
~~~

The root manifest identifies the complete run. Every stage manifest records the
same Run ID together with the resolved configuration, BoundEvo version, Python
runtime, platform, relevant dependency versions, source revision when available,
and output locations.

An explicit Run ID can be supplied when orchestration requires a stable external
identifier:

~~~bash
boundevo pipeline   --config configs/pipeline.json   --run-id cec2017-main-001
~~~

Existing run directories are never overwritten.

## Convergence history

Benchmark and parent-count experiments export sampled optimization history.
The default interval is 100 generations:

~~~json
{
  "history_interval": 100
}
~~~

Every trial always keeps generation 0 and the final optimizer state. Sampling
reduces the result size substantially for high evaluation budgets while retaining
enough points for convergence visualization.

Benchmark history contains:

~~~text
function_id
function_name
dimension
method
repeat
seed
generation
evaluations
best_objective
best_error
best_violation
worst_objective
worst_violation
~~~

The parent-count history adds `parent_count`.

## Standalone HTML report

The managed pipeline generates `report/report.html`. The report embeds SVG
graphics directly and therefore remains viewable without Python, Matplotlib,
JavaScript, or a web server.

It contains:

- benchmark mean ranks and Win/Tie/Loss;
- aggregate runtime and function-evaluation summaries;
- sampled convergence curves, averaged across repeated trials;
- parent-count M-sensitivity curves;
- coefficient-generation efficiency curves;
- reproducibility manifests.

History curves are downsampled again for rendering so a large CSV does not
produce an unnecessarily large HTML document.

## Manual stage-by-stage workflow

The stages can still be executed independently:

~~~bash
boundevo benchmark --config configs/cec2017.json
boundevo sweep --config configs/parent_sweep.json
boundevo efficiency --config configs/efficiency.json
boundevo analyze --config configs/analysis.json
boundevo report --config configs/report.json
~~~

Each command generates its own Run ID if one is not supplied. Use `--run-id`
when an external experiment registry should control the identifier.

## Statistical analysis

The analysis stage reports average ranks, Win/Tie/Loss comparisons, paired
Wilcoxon signed-rank tests with Holm correction, and the Friedman omnibus test.
The complete managed pipeline requires at least three selected methods when the
statistical stage is enabled.

For infrastructure smoke tests or single-method debugging, set:

~~~json
{
  "statistical_analysis": false
}
~~~

in a pipeline configuration.

## Result management

The `results/` directory is ignored by Git. Curated tables, figures, or reports
should be copied into a deliberate publication or documentation directory before
committing them. This prevents raw benchmark output and repeated-run directories
from polluting the repository history.


## Publishing experiment evidence to both READMEs

BoundEvo README charts are generated from committed, *real* CSV results.
Do not manually substitute simulated observations or reconstruct outcomes from
narrative claims.

The featured and historical experiment directories are configured in
[configs/readme_results.json](../configs/readme_results.json). The generator is
[scripts/update_readme_results.py](../scripts/update_readme_results.py).

~~~bash
python scripts/update_readme_results.py
python scripts/update_readme_results.py --check
~~~

This updates:

- `README.md` and `README_CN.md`: numerical tables, research parameters,
  interpretation limitations, source links, and embedded charts.
- `docs/figures/cec2017-30d-relative-error.svg`: per-function error ratios
  normalized to the RE baseline, with logarithmic scaling.
- `docs/figures/cec2017-30d-runtime.svg`: observed wall-clock time by method.
- `docs/figures/cec2017-30d-29function-screen.svg` (after the independent
  29-function screen is published): winners by *observed mean*, not a
  statistical significance claim.

The [README evidence workflow](../.github/workflows/readme-evidence.yml)
automatically regenerates and commits figures and both READMEs when the
configured CSV source, environment metadata, or generator changes. It also
validates SVG XML structure. Unit tests exercise the plotting functions
against the recorded experimental metadata and synthetic edge-case fixtures;
these tests are not substitutes for actual optimization experiments.

A new experiment should be made the featured one **only after** its raw CSV,
summary, environment/seed metadata and validity checks have been committed.
Change the config path, run the generation script, inspect the resulting
tables/figures, and retain links to previous experiments in a clearly labeled
historical section. Never combine results with different backends or
evaluation budgets in a single unqualified summary.
