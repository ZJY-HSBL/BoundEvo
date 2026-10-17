# Full-suite CEC2017 30D: 10,000-FE exploratory study

## Protocol

- 29 official CEC2017 functions (F1 and F3–F30), 30 dimensions.
- ABC, EDBF, RE; three independent paired initial seeds per function.
- 10,000 objective evaluations per trial, including 100 initialization.
- Fixed N=100, M=15, K=5, L=1, history sampled every 500 generations.
- Independent reference-derived CEC2017 backend, pinned to 424a9fa2757914c3e4cfdd8f59a268b1aeb3197f.
- Completed **261 real trials**, strictly validated.

## Observed function-level leaders and mean ranks

| Method | Function-level mean leaders | Average rank (lower better) |
|:---|---:|---:|
| ABC | 27 | 1.069 |
| EDBF | 1 | 2.897 |
| RE | 1 | 2.034 |

Friedman statistic: 48.4828, asymptotic p=2.96553e-11 (29 function-level matched groups).

### Paired Wilcoxon on log10 function-level mean error

| Contrast | ABC lower / higher | Unadjusted p | Holm-adjusted p |
|:---|---:|---:|---:|
| abc_vs_edbf | 28 / 1 | 7.45058e-09 | 1.49012e-08 |
| abc_vs_re | 28 / 1 | 1.11759e-08 | 1.49012e-08 |

## Detailed function results (mean objective error)

| Function | ABC | EDBF | RE | Lowest observed mean |
|:---|---:|---:|---:|:---|
| F1 | 1.32059e+11 | 3.33051e+11 | 1.53709e+11 | ABC |
| F3 | 31980.2 | 275529 | 145773 | ABC |
| F4 | 915.069 | 7212.66 | 1048.81 | ABC |
| F5 | 279.516 | 419.52 | 317.72 | ABC |
| F6 | 48.218 | 100.58 | 71.6097 | ABC |
| F7 | 441.651 | 1754.95 | 693.418 | ABC |
| F8 | 273.217 | 402.399 | 318.512 | ABC |
| F9 | 3853.2 | 18373.9 | 9431.36 | ABC |
| F10 | 7300.59 | 7715.86 | 7773.05 | ABC |
| F11 | 281.755 | 3532 | 691.517 | ABC |
| F12 | 2.24692e+07 | 1.37333e+10 | 2.40775e+09 | ABC |
| F13 | 16042.5 | 2.46343e+09 | 2.62372e+07 | ABC |
| F14 | 295.59 | 19196.9 | 435.416 | ABC |
| F15 | 810.331 | 1.47027e+07 | 50695.6 | ABC |
| F16 | 2327.54 | 2610.18 | 2257.26 | RE |
| F17 | 883.289 | 1368.51 | 1125.7 | ABC |
| F18 | 406.682 | 5.19326e+06 | 757109 | ABC |
| F19 | 206.617 | 5.63694e+07 | 1.34963e+06 | ABC |
| F20 | 682.231 | 1188.36 | 953.258 | ABC |
| F21 | 458.595 | 589.088 | 486.105 | ABC |
| F22 | 7889.53 | 7725.79 | 7904.77 | EDBF |
| F23 | 694.93 | 809.138 | 728.456 | ABC |
| F24 | 763.247 | 841.157 | 828.39 | ABC |
| F25 | 736.017 | 3931.09 | 1013.16 | ABC |
| F26 | 4284.35 | 6036.81 | 4558.32 | ABC |
| F27 | 568.772 | 633.545 | 593.387 | ABC |
| F28 | 1129.9 | 2898.3 | 1301.99 | ABC |
| F29 | 1310.56 | 1925.12 | 1920.11 | ABC |
| F30 | 459541 | 6.32343e+07 | 4.88896e+06 | ABC |

## Critical interpretation limits

- Three repetitions per function provide limited within-function variance precision, and the function-level hypothesis tests should be exploratory.
- The 29 benchmark functions share construction and are not 29 independent draws from all possible optimization problems.
- An objective evaluation budget of 10,000 is not the 100,000-FE source paper budget; results cannot be cited as full source reproduction.
- Comparisons of wall-clock time are runner- and Python-specific.
- The pinned NumPy benchmark implementation derives from C but is not the organizers' official original C binary.
- Do not pool this experiment with the earlier 1,200-FE or four-function 3,000/10,000-FE cohorts.

## Reproducibility

All 261 trials and every convergence checkpoint are provided in the adjacent `trials.csv` and `history.csv`, with `summary.csv`, `function_ranks.csv` and `environment.json`.
