# Cross-run registry and Pareto comparison (v0.5)

BoundEvo discovers finished and unfinished runs by scanning the managed
`results/runs/` directories created by `boundevo pipeline`. The registry is
read-only and requires no database, daemon, or mutable index file.

## Discover runs

~~~bash
boundevo runs --root results/runs
boundevo runs --root results/runs --only-complete
boundevo runs --root results/runs --json
boundevo runs --root results/runs --verbose
~~~

The registry reports the run ID, status, benchmark dimension, methods,
evaluation budget, and repetition count. Runs with missing output files remain
visible as `incomplete`; malformed or mismatching manifests are shown as
`invalid`. Comparisons use only `complete` runs.

## Compare runs

Compare all complete runs in one directory:

~~~bash
boundevo compare --root results/runs
~~~

Compare two selected runs and save the comparison:

~~~bash
boundevo compare \
  --root results/runs \
  --run-id experiment-001 \
  --run-id experiment-002 \
  --output results/cross_run_comparison.md
~~~

Each benchmark row is identified by the full key
`(function_id, dimension, method)`. Both runs must contain the same benchmark
case set by default. If the sets differ, the command refuses to compare them.

To explicitly compare only shared cases, opt in:

~~~bash
boundevo compare \
  --root results/runs \
  --run-id experiment-001 \
  --run-id experiment-002 \
  --allow-partial
~~~

Partial results are marked as such and MUST NOT be described as covering the
excluded benchmarks.

## Criteria

Every selected run is scored on its common case cohort using:

- arithmetic mean CEC2017 objective error (lower is better);
- arithmetic mean measured runtime in seconds (lower is better);
- arithmetic mean function evaluations (lower is better).

The script reports a separate leader for every criterion. It does NOT declare
an overall best run without user-defined priorities.

A run belongs to the three-objective Pareto front if no other compared run has
values no worse across all three criteria and a strictly better value on at least
one criterion. Distinct runs with identical metric vectors are both nondominated.

## Interpretation limitations

A case-aligned comparison is NOT necessarily a controlled causal comparison:

- Differing evaluation budgets change the optimization opportunities.
- Wall-clock time measured on different platforms is not hardware-normalized.
- Different code revisions may contain several changes.
- Different repetition counts imply different estimation uncertainties.
- The mean raw objective error is scale-dependent across functions.

The generated report flags budget, platform, revision, repetition, and partial
coverage differences. Pareto membership is a descriptive trade-off property,
not a statistical significance test. Use controlled paired runs and suitable
uncertainty analyses before claiming an algorithmic improvement.

## Scope

The registry intentionally reads only a fixed set of relative artifacts from
each run bundle: the root `manifest.json` and
`benchmark/summary.csv`, plus checking `report/report.html`. It never follows
arbitrary output paths listed in manifests and never modifies experiment data.
