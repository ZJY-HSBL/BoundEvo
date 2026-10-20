# CEC2017 F16/F22 anytime research: measured 10k–100k trajectories

Reuse the previously completed **120 real 100k-evaluation optimization runs**, 20 paired seeds per method/function. This is a **new analysis of existing trajectories, not 120 additional runs**.

Following the anytime-performance view of black-box optimization, the primary exploratory outcome is the sample-and-hold integral of `log1p(best-so-far error)` over `log(FE)` from FE=10,000 to FE=100,000, divided by `log(10)`. Smaller means better anytime performance. The checkpoint step approximation does not reconstruct changes between measurements.

## Log-budget anytime loss (lower is better)

| Function | Method | Mean | 95% bootstrap mean CI |
|:---|:---|---:|:---|
| F16 | ABC | 7.47964 | [7.41546, 7.53866] |
| F16 | EDBF | 7.76795 | [7.74631, 7.78825] |
| F16 | RE | 7.65236 | [7.62212, 7.67878] |
| F22 | ABC | 8.28421 | [7.87333, 8.65111] |
| F22 | EDBF | 8.80646 | [8.64329, 8.90924] |
| F22 | RE | 8.62158 | [8.31211, 8.85649] |

## Paired anytime contrast and uncertainty

| Function | Contrast | ABC W/L/T | mean comparator−ABC | Bootstrap 95% CI | Holm p |
|:---|:---|---:|---:|:---|---:|
| F16 | abc_vs_edbf | 19/1/0 | +0.28831 | [+0.21771, +0.36203] | 0.000160217 |
| F16 | abc_vs_re | 15/5/0 | +0.17271 | [+0.09728, +0.25113] | 0.124168 |
| F22 | abc_vs_edbf | 13/7/0 | +0.52226 | [+0.15729, +0.93706] | 0.526352 |
| F22 | abc_vs_re | 11/9/0 | +0.33737 | [-0.04896, +0.77831] | 0.823803 |

## Fixed baseline-derived target profiles

For each function, take the 25th, 50th, 75th percentiles of 60 pooled 10k-FE endpoint errors across all methods. Each method has 20 seeds × 3 thresholds = 60 descriptive target-seed pairs. Percentages show pairs whose best error reached the respective target **at a sampled checkpoint by the stated FE budget**. Targets were chosen after seeing the 10k historical values and are not blinded confirmation.

| Function | Method | 10k attainment | 100k attainment |
|:---|:---|---:|---:|
| F16 | ABC | 85.0% | 100.0% |
| F16 | EDBF | 16.7% | 88.3% |
| F16 | RE | 48.3% | 100.0% |
| F22 | ABC | 61.7% | 91.7% |
| F22 | EDBF | 51.7% | 88.3% |
| F22 | RE | 36.7% | 88.3% |

## Integrity and interpretation

- All 120 experimental keys and 13,440 history rows verified; all trajectories have 112 unique checkpoints, exact original 10k and 100k outcomes and monotone best-so-far records.
- Bootstrap replicates re-sample **paired seed indices** rather than treating four comparisons, many times, or three targets as independent.
- Exact two-sided paired sign tests were Holm-adjusted for the four within-analysis comparisons. This exploratory analysis is post-hoc and does not adjust for other comparisons made across previous releases.
- Within-function objectives can be compared across methods; absolute errors are not pooled across differently scaled F16 and F22 landscapes.
- Reference-derived CEC2017 Python backend, not the official C binary. The two functions were selected adaptively in earlier work.

## Sources

[120 published original trials](../cec2017-paperbudget-30d-100k-20seeds-2026-10-19/trials.csv) · [13,440 original convergence states](../cec2017-paperbudget-30d-100k-20seeds-2026-10-19/history.csv) · [new anytime summaries](anytime_summary.csv) · [four paired contrasts](anytime_paired.csv) · [empirical attainment profiles](target_profiles.csv) · [recorded protocol](../../fresh_function_replication_protocol.md)
