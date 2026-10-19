# CEC2017 F16/F22: paired 10k-to-100k evaluation budget study

30 completed trials (2 functions × 3 coefficient generators × 5 seeds), D=30, capped at 100,000 function evaluations per trial. The same five seeds are a subset of the earlier **20-seed** 10,000-evaluation holdout (not 5 fresh additional seeds).

The prior observed 10k errors are verified against exact FE=10000 checkpoints inside each continuing 100k optimization trajectory.

| Function | Method | 10k mean error | 100k mean error | Improvement |
|:---|:---|---:|---:|---:|
| F16 | ABC | 2341.15 | 1732.43 | +26.00% |
| F16 | EDBF | 2577.72 | 2076.05 | +19.46% |
| F16 | RE | 2381.88 | 1797.66 | +24.53% |
| F22 | ABC | 6170.17 | 5780.24 | +6.32% |
| F22 | EDBF | 7879.72 | 7155.37 | +9.19% |
| F22 | RE | 7981.51 | 5180.38 | +35.10% |

## Interpretation limits

- Five matched seeds per function provide exploratory convergence trajectories, not robust statistical evidence of superiority.
- 100,000 evaluations match the source-paper upper budget but only two of 29 official CEC2017 functions are included.
- These runs use the pinned independent Python CEC2017 reference port; it is not the original organizers' C benchmark binary.
- Because these seeds were used in the previous 10k holdout, do not call them an independent 5-seed validation cohort.
- A best-so-far objective cannot worsen with a higher evaluation budget for the **same deterministic run**; the scientific question is how the *relative efficiency and convergence rates* change.

## Source evidence

[30 original trials](trials.csv) · [sampled convergence curves](history.csv) · [per-method means](summary.csv) · [run manifests](environment.json)
