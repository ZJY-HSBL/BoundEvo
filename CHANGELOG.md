# Changelog

All notable changes to BoundEvo are documented here.

## [Unreleased]

### Added

- JSON reproducibility manifests for benchmark, sweep, efficiency, analysis, and report commands.
- Environment capture for Python, NumPy, SciPy, opfunu, Matplotlib, platform, and source revision.
- Standalone HTML experiment report combining benchmark rankings, operational metrics, parent-count results, coefficient-generation efficiency, and manifests.
- `boundevo report` command and `configs/report.json` preset.
- Research workflow documentation for a complete experiment-to-report pipeline.

### Changed

- Development version advanced to `0.4.0.dev0`.
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
