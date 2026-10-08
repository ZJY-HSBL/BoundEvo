# Research workflow

BoundEvo keeps optimization, experiment execution, statistical analysis, and
reporting as separate stages. This makes every stage inspectable and lets a run
be repeated without relying on undocumented shell history.

## 1. Install the experiment environment

~~~bash
pip install -e ".[cec2017,analysis,plot]"
~~~

## 2. Run the benchmark

~~~bash
boundevo benchmark --config configs/cec2017.json
~~~

The command writes the raw trials, summary statistics, and a JSON run manifest.
The manifest records the resolved configuration, BoundEvo version, Python
version, platform, dependency versions, source revision when available, and
output paths.

## 3. Run the parent-count and coefficient-efficiency studies

~~~bash
boundevo sweep --config configs/parent_sweep.json
boundevo efficiency --config configs/efficiency.json
~~~

Both commands emit their own manifests, so runtime results can be linked to the
environment that produced them.

## 4. Run statistical analysis

~~~bash
boundevo analyze --config configs/analysis.json
~~~

The analysis stage reports average ranks, Win/Tie/Loss comparisons, paired
Wilcoxon signed-rank tests with Holm correction, and the Friedman omnibus test.

## 5. Build a standalone report

~~~bash
boundevo report --config configs/report.json
~~~

The HTML report is dependency-free at viewing time. It combines benchmark
ranking, operational summaries, the parent-count study, coefficient-generation
efficiency, and available run manifests into one portable file.

## Artifact set

A complete run can produce:

~~~text
results/
├── cec2017_trials.csv
├── cec2017_summary.csv
├── cec2017_manifest.json
├── parent_sweep_trials.csv
├── parent_sweep_summary.csv
├── parent_sweep_tables.md
├── parent_sweep_manifest.json
├── coefficient_efficiency.csv
├── coefficient_efficiency_manifest.json
├── statistical_analysis.md
├── analysis_manifest.json
├── report.html
└── report_manifest.json
~~~

Large result files remain ignored by Git by default. Commit only curated result
tables or figures when they are intended to become part of a published
benchmark snapshot.
