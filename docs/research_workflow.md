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
