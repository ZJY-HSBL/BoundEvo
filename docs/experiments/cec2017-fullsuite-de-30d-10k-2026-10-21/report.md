# Full 29-function CEC2017 comparison with generational DE/rand/1/bin

**435 original optimization trials**, F1/F3–F30, D=30, 10k FE, five matched new seeds per function, ABC / ABC-Reverse / DE/rand/1/bin. **43,500 real convergence checkpoint rows**; common sampled initial population for each function and seed. New benchmark control used F=0.8, CR=0.9, NP=100, forced binomial donor coordinate, generational greedy one-to-one replacement and box projection. These are one fixed baseline configuration, not an exhaustive DE hyperparameter search.

## Global function-block result

| Method | Average function rank (smaller better) | Functions with smallest mean error |
|:---|---:|---:|
| abc | 1.0690 | 27/29 |
| abc_reverse | 2.1034 | 2/29 |
| de_rand1bin | 2.8276 | 0/29 |

Friedman function-rank statistic = **45.3103**; random-label block permutation p = **4.99975e-05**, 20,000 fixed-RNG resamples. This inference assumes function-block algorithm-label exchangeability under the null, and only covers the CEC2017 function collection. It is not evidence for all optimizers/problems.

### Across-function pairwise directions (Holm-adjusted across three tests)

| Comparator | A wins / B wins / ties (29 functions) | Exact sign p | Holm p |
|:---|---:|---:|---:|
| abc vs de_rand1bin | 29/0/0 | 3.72529e-09 | 1.11759e-08 |
| abc vs abc_reverse | 27/2/0 | 1.62423e-06 | 3.24845e-06 |
| abc_reverse vs de_rand1bin | 24/5/0 | 0.000546113 | 0.000546113 |

These tests compare **within-function five-seed means** and account for function scales by using direction of advantage, not raw average error. They do **not** test each individual function at five-seed resolution.

## All 29 empirical function means

| Function | ABC | ABC-Reverse | DE/rand/1/bin |
|:---|---:|---:|---:|
| F1 | 1.75296e+11 | **1.02943e+11** | 3.53352e+11 |
| F3 | **33862.3** | 132958 | 233613 |
| F4 | **1062.39** | 1955.38 | 3712.72 |
| F5 | **284.821** | 309.002 | 394.241 |
| F6 | **55.2575** | 68.2433 | 100.826 |
| F7 | **449.061** | 535.106 | 1748.73 |
| F8 | **275.878** | 312.199 | 388.691 |
| F9 | **4950.75** | 6329.25 | 16739.6 |
| F10 | **7536.84** | 7583.04 | 7884.91 |
| F11 | **312.301** | 551.781 | 3455.96 |
| F12 | **5.41792e+07** | 1.27309e+09 | 1.26608e+10 |
| F13 | **19343** | 1.208e+07 | 2.43354e+09 |
| F14 | **252.857** | 321.675 | 49894.8 |
| F15 | **697.092** | 16664.2 | 4.8775e+07 |
| F16 | **2098.55** | 2104.11 | 2375.67 |
| F17 | 975.649 | **937.291** | 1262.9 |
| F18 | **471.9** | 101762 | 1.01876e+07 |
| F19 | **173.794** | 204154 | 1.90671e+08 |
| F20 | **821.002** | 1113.73 | 965.863 |
| F21 | **456.114** | 487.62 | 558.427 |
| F22 | **3616.65** | 7923.1 | 7705.53 |
| F23 | **658.504** | 792.231 | 699.89 |
| F24 | **707.142** | 861.853 | 754.291 |
| F25 | **922.03** | 1046.28 | 3417.49 |
| F26 | **4556.42** | 4691.46 | 5098.85 |
| F27 | **551.57** | 665.481 | 660.674 |
| F28 | **774.978** | 1159.32 | 2156.59 |
| F29 | **1617.2** | 1731.05 | 1956.33 |
| F30 | **44372.8** | 4.0184e+06 | 1.12997e+08 |

### Scientific evidence and interpretation boundaries

- Exactly 29 retained official CEC2017 function IDs, excluding the withdrawn F2.
- Backend: pinned independent C-derived Python reference, *not* CEC organizers' original C.
- All 435 runs reached FE=10,000 with exactly 100 unique checkpoints; every endpoint and initial paired value was cross-validated.
- All 435 optimizer runs are new, **not** the previously published 144-run or 200-run mechanism and limited-function cohorts.
- All reported significance is exploratory; curated functions are not a random sample of general optimization tasks. Five seeds per function and fixed DE hyperparameters leave considerable uncertainty.
- Equal function evaluations do not imply equal iteration count or equal wall-clock cost. The DE baseline has no local polishing.

[435 original trials](trials.csv) · [43,500 checkpoints](history.csv) · [87 function-method bootstrap summaries](summary.csv) · [87 function ranks](function_ranks.csv) · [three corrected function-sign tests](function_sign_tests.csv) · [global rank and permutation statistics](global_statistics.json) · [exact environment and shard provenance](environment.json) · [frozen protocol](../../fullsuite_de_protocol.md)
