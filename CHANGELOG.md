# Changelog

All notable changes to BoundEvo are documented here.

## [0.10.0] - 2026-10-18

### Independent-seed robustness experiment

- Finished 120 actual optimization trials: F16/F22, D=30, 10,000 FEs, three
  coefficient generators and 20 newly sampled paired initial seeds.
- Confirmed the two uncertain function mean-error rankings switch to ABC
  on new seeds, while distinguishing F16's significant adjusted exact sign
  tests from nonsignificant paired F22 sign tests.
- Reported percentile-bootstrap 95% confidence intervals for mean objective
  error, 10,000 paired resamples of log1p error advantage, and Holm correction
  across four prespecified comparisons.
- Published original trials, summary statistics, backend preflight results,
  environment metadata and experimental protocol in GitHub.
- Embedded a data-generated bootstrap whisker SVG in English/Chinese READMEs
  alongside observed 3-, 10- and 20-seed winner comparisons.
- Added validation of seed disjointness, paired-method coverage,
  function-evaluation budgets and recomputed README means.
- All findings are exploratory and specific to the independent Python CEC2017
  reference implementation, not the original official C binary.

## [0.9.0] - 2026-10-17

### Real full-suite experiments and research visualizations

- Completed all 261 actual CEC2017 trials at D=30, with 29 official functions,
  three coefficient generators, three paired random seeds, and 10,000 FEs.
- Recorded, archived, and validated 5,481 convergence states from four
  independently executing experiment shards.
- Published function-level mean errors, average ranks, Friedman test,
  exploratory Wilcoxon comparisons and Holm-adjusted p values.
- Automatically generated new 29-function winner, four-function convergence
  and 1,200-to-10,000-FE leaderboard-transition SVG charts.
- Added expandable all-29-function empirical error tables to both READMEs.
- Confirmed measured leader changes on F16, F20 and F22 as evaluation budget
  increased, while preserving the earlier 10-seed F22 result separately.
- Documented full-suite experiment design, scientific limitations,
  run provenance and strict CSV/history integrity checks.

## [0.8.0] - 2026-10-17

### Research experiments and presentation

- 120 real 30D CEC2017 trials on F10/F20/F22/F30 (three methods, ten matched seeds, 10,000 evaluations each).
- Reconciled trial-level mean-error CSVs with README figures, generated Markdown analysis and pinned runtime metadata.
- Two new SVGs showing measured 10k-FE relative errors and 3k-to-10k-FE budget sensitivity.
- Eight exact paired sign tests jointly Holm-adjusted and shown in both README versions and Chinese research report.
- Added source-data validation to reject wrong seeds, missing/duplicate trials, invalid budgets and summary/CSV mismatches.
- Documented purposive case selection and the statistical interpretation limits.

## [0.7.0] - 2026-10-17

### Research evidence and documentation

- Generate bilingual README result tables and publication-style SVG charts directly from committed experimental CSV files.
- Record feature datasets in `configs/readme_results.json`, with GitHub Actions regeneration.
- Add a standalone all-29-function 30D screening workflow with matched initial random seeds and per-function numerical checks.
- Automatically feature the 29-function screening chart in both READMEs when verified data are published.
- Add tests and a documented workflow for reproducible README figures.

## [0.6.0] - 2026-10-17

### Added

- Independent C-derived CEC2017 Python reference backend, pinned upstream, alongside opfunu.
- 58 sampled function/dimension integrity checks across official F1,F3..F30 at D=10/30.
- 120 actual D=30 trials across F1,F3,F10,F30 with paired seeds and objective budgets.
- Exact paired sign-test analysis with Holm multiple-comparison correction.
- Matched initial RNG seeds across algorithms in benchmark and parent-count workflows.
- Reference backend selection from Python/CLI/pipeline and corresponding regression tests.
- Full experiment data, scientific caveats and numerical integrity issue tracking.

### Experimental validation

- Completed 60 actual paired-seed CEC2017 pilot trials on F1, F3, F5, F20 (D=10, 1500 FEs, 5 repeats for each of ABC/EDBF/RE).
- Published immutable raw and summary CSVs, chart, and runner environment snapshot under docs/experiments/.
- Fixed official CEC2017 ID mapping to opfunu's renumbered classes.
- Added a fail-fast check against objective values below the reported optimum.
- Identified numerical integrity problems with opfunu F10 and F30; full 29-function benchmark validation remains open (issue #3).

## [0.5.0] - 2026-10-16

### Added

- Read-only Run Registry for complete, incomplete, and malformed experiment bundles.
- `boundevo runs` command with compact and JSON output.
- Aligned cross-run comparison based on matching CEC function, dimension, and method.
- Per-criterion leaders for mean objective error, runtime, and function evaluations.
- Three-objective Pareto-front identification without unsupported overall ranking.
- `boundevo compare` command with explicit optional partial-case comparison.
- Documentation and integration tests covering comparability and validity.

## [0.4.0] - 2026-10-08

### Added

- JSON reproducibility manifests for benchmark, sweep, efficiency, analysis, and report commands.
- Environment capture for Python, NumPy, SciPy, opfunu, Matplotlib, platform, and source revision.
- Standalone HTML experiment report combining benchmark rankings, operational metrics, parent-count results, coefficient-generation efficiency, and manifests.
- `boundevo report` command and `configs/report.json` preset.
- Research workflow documentation for a complete experiment-to-report pipeline.
- Unique managed Run IDs and non-overwriting `results/runs/<run-id>/` experiment bundles.
- Sampled convergence-history CSV export for benchmark and parent-count studies.
- Inline SVG convergence, M-sensitivity, and efficiency curves in the standalone report.
- End-to-end `boundevo pipeline` command and `configs/pipeline.json` preset.

### Changed

- Package version advanced to `0.4.0`.
- Existing CLI commands now write manifests by default.

## [0.3.0] - 2026-10-08

### Added

- Source-aligned CEC2017 benchmark runner covering F1 and F3-F30.
- Parent-count sweep for M=10..16 on F1, F10, F20, and F30.
- Vectorized coefficient-generation efficiency experiment for M=1..20.
- Unified boundevo command-line interface with JSON experiment presets.
- Automatic method ranking and Win/Tie/Loss summaries.
- Paired Wilcoxon signed-rank tests with Holm correction.
- Friedman omnibus test across multiple methods.
- CSV, Markdown, and plotting workflows for reproducible experiments.
- CI smoke tests for CEC2017, parent-count sweeps, efficiency estimation, CLI, and statistical analysis.

### Changed

- Reorganized the README around installation, CLI workflows, reproduction, and validation.
- Kept benchmark dimensionality explicit because the extracted experiment-setting text does not state it.
- Version promoted to 0.3.0.

### Reproduction notes

- Main source-aligned settings: N=100, M=15, K=5, L=1.
- Parent-count study: M=10..16 on F1, F10, F20, F30.
- The adaptive-boundary coefficient generator produces a valid coefficient vector in one pass.
- The source flowchart has an indexing ambiguity around the final coefficient; BoundEvo documents and uses the mathematically consistent M-dimensional interpretation.
