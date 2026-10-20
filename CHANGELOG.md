# Changelog

All notable changes to BoundEvo are documented here.

## [Unreleased]

## [0.12.0] - 2026-10-20

### Deterministic ABC-Reverse mechanism study and 144 new optimizer trials

- Introduced `abc_reverse`, a deterministic positional reversal of the exact ABC coefficient vector. The control conserves the full coefficient multiset, bounded affine sum, one-attempt feasibility, and RNG usage at each coefficient-generation call.
- Completed **144 new real matched-seed CEC2017 runs** (F10/F16/F20/F22 at 30D and 10k FE, ABC vs ABC-Shuffle vs ABC-Reverse, 12 fresh paired seeds each) and archived 3,312 original convergence checkpoints with complete provenance checks.
- Calculated method summaries, 10,000 paired-bootstrap intervals and 8 exact paired sign tests jointly corrected by Holm. Original ABC had lower mean errors than ABC-Reverse on all four functions, but **none of the eight corrected pairwise tests was significant**; F10 ABC-Shuffle had the smallest mean error.
- Audited **50,000 valid ABC coefficient vectors** and documented the observed **42.23% elite-slot share of absolute coefficient weight** for the first five of 15 parent slots, a positional diagnostic rather than proof of optimization benefit.
- Added two new original-data SVG charts, a frozen mechanism protocol, verified data-derived bilingual README results and a four-shard fail-closed CI experiment workflow.
- Existing v0.11.1 studies of 200 additional runs are retained; earlier 120 long-budget anytime trajectories are not counted as new trials.

## [0.11.1] - 2026-10-20

### 2026-10-20: Independent-seed replication and coefficient-order ablation

- Reanalysed the **existing 120 F16/F22 100k-FE optimizer trajectories** using integrated log-budget anytime loss, paired bootstrap confidence intervals and 10k baseline-derived empirical target-attainment profiles. Reused trajectories are not counted as new runs.
- Executed and published **120 new, independent-seed, 10k-FE CEC2017 trials** on F3/F10/F20/F30 at 30D, comparing ABC/EDBF/RE with ten newly matched seeds/function, original checkpoints, eight Holm-adjusted paired tests and a measured-data four-panel bootstrap CI figure.
- Found function-dependent performance: ABC achieved the smallest observed mean error on F3/F20/F30, and RE on F10. ABC's F3/F30 comparisons passed this study's Holm-adjusted exact sign tests; F10/F20 tests did not.
- Added the **ABC-Shuffle** diagnostic generator, preserving the original ABC coefficient multiset but randomizing assignment to elite-first ordered parents, with validation and deterministic reproducibility tests.
- Executed and published **80 additional real 10k-FE CEC2017 ablation trials** on F10/F16/F20/F22 with further unused matched seeds. ABC had smaller measured means than ABC-Shuffle across all four functions, but all Holm-adjusted paired sign tests remained nonsignificant.
- Published **six new scientific, original-data-derived SVG figures**, archived paired-trial and checkpoint evidence, recorded methodological limits, and regenerated English/Chinese research sections. Recorded protocols distinguish new runs from post-hoc analysis and adaptive choice of functions. The v0.11.0 release tag remains unchanged.

## [0.11.0] - 2026-10-19

### Matched 100k-budget optimization validation

- Completed 120 real 100,000-FE CEC2017 F16/F22 optimization trajectories (30D, ABC/EDBF/RE, 20 paired seeds each), reusing 30 previously verified runs and newly computing 90 runs.
- Independently checked every trajectory against its previously published exact 10k checkpoint; committed 13,440 convergence states with seed, provenance, budget and numerical invariants.
- Reported 100k mean objective errors, bootstrap 95% intervals and four paired two-sided exact sign tests with Holm correction; ABC had the lowest observed F16/F22 mean but F22 pairwise superiority remained statistically unsupported.
- Marked the 20-seed extension as exploratory/adaptive rather than independent confirmation; retained fixed C-derived reference backend and two-function generalization limits.
- Published bilingual README comparisons, regenerated actual-data SVG curves, reproducibility records, and a six-shard experimental workflow with fail-closed evidence validation.
- Built an auditable release package after Python 3.10–3.12 tests, linting, scientific consistency checks, and wheel/sdist validation.

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
