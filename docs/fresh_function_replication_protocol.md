# BoundEvo independent-seed cross-function replication protocol

Recorded **before** starting this new workflow (2026-10-20).

## Question and rationale

The long-budget (100k FE) F16/F22 adaptive follow-up does not test transfer of
observed performance to other CEC2017 problem classes. We therefore run a separate
**fresh-random-seed** replication at F3, F10, F20 and F30 with the three existing
coefficient generators, keeping other optimizer settings fixed.

The function selection is **informed by previous studies**, not blinded or
randomly sampled. This is an independent *seed cohort*, but **not an independent
selection-blind confirmation** of a universal advantage. No new algorithm is
claimed or benchmarked in this experiment.

## Frozen experiment design

- Functions **F3, F10, F20, F30** (CEC2017; fixed C-derived reference backend
  `424a9fa2757914c3e4cfdd8f59a268b1aeb3197f`), dimension **30**.
- Methods **ABC**, **EDBF**, and **RE**, with population size 100, parent count
  15, elite parent count 5, one offspring per generation. Same search domain and
  selection code, differing only in coefficient generation.
- **10,000 objective evaluations/run**, **10 fresh paired seed IDs per function**,
  seeds `20261079 + 10000 * function_id + repeat` with repeat 0–9.
- Exactly **120 original optimizer runs**, four function-sharded jobs.
- The same repeat and function get identical initial populations across the
  three methods, asserted from the first FE=100 record.
- Keep original trials, sampled best-so-far history, individual job manifests
  and complete optimizer/checkpoint provenance. Reject missing or duplicated
  trials and any infeasible objective value below the declared optimum.
- **Eight two-sided paired exact sign tests**, ABC vs EDBF and ABC vs RE for
  each of four functions; Holm-corrected as a single family of 8 exploratory
  contrasts. Use reproducible 10,000 paired-seed bootstrap replicates for
  intervals on mean errors and paired mean log1p advantages.
- Report distributions and uncertainty, not just the lowest mean. Do not
  combine this cohort with prior random seed sets or represent a new 10k
  experiment as a 100k experiment.

## Separate anytime analysis

A separate analysis will reuse the **120 already existing 100k F16/F22 runs**
(no new runs) to answer whether endpoint rankings persist across the
10k–100k budget interval.

Define per-run log-budget anytime loss as the sample-and-hold integral of
`log(1 + best_so_far_error)` against `log(FE)`, divided by
`log(100000/10000)`. The plotted and tested quantity is therefore a
dimensionless average log1p error; **lower is better**. It is a
checkpoint-sampled approximation, not a continuous-time integral.

Define target-error thresholds from the **pooled 10k-FE cohort values across
all methods** for each function, using 25th, 50th and 75th percentiles.
These are post-hoc, method-neutral difficulty levels. Report empirical
target-hit fractions from checkpointed traces, with no assumption of exact
first-hitting times between checkpoints. For within-function comparisons use
paired seed differences and bootstrap confidence intervals; adjust four
sign tests for ABC vs EDBF and ABC vs RE at F16 and F22 by Holm.
This analysis is descriptive/exploratory and does not cancel earlier
adaptive selection or multiple research stages.

## Publication gates

Publish tables, charts and README updates **only after** 120 real new trials
and all original checkpoint records pass numerical integrity, provenance,
coverage, and CI checks. No partial source data or fabricated curves.
