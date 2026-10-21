# Calibrated differential evolution and jDE: fresh-seed comparison

**822 genuine original optimizer runs** in two explicitly separate cohorts: **72 calibration trials** on development CEC2017 [3, 10, 20, 30] (six conventional DE parameter candidates × 4 functions × 3 seeds), followed by **750 fresh-seed evaluation runs** on the remaining 25 retained CEC functions (ABC, one frozen calibrated DE, jDE × 25 functions × 10 seeds). Stored best-so-far records: **7,200 calibration checkpoints** and **75,000 evaluation checkpoints**. The evaluation seeds are never used for DE calibration.

## Development-only winner

Selected **best050cr090**: strategy best1bin, F=0.5, CR=0.9. Average rank on four development functions = **1.5000**. All six calibration candidates, objective values and source manifests are archived. Function choice is transparent, not a blind sample.

## Evaluation-only function-block summary

| Algorithm | Mean rank (lower better) | Lowest-mean-error functions | Hosted-runner mean seconds/run |
|:---|---:|---:|---:|
| abc | 2.2000 | 8/25 | 3.134 |
| de_tuned | 1.8400 | 9/25 | 2.014 |
| jde | 1.9600 | 8/25 | 1.832 |

Function-rank Friedman Q=**1.68000**, 20,000-label permutation p=**0.4507775**. This is exploratory inference across curated and previously observed benchmark functions, not a distribution-free statement about all optimization problems.

| Predeclared comparison | ABC function wins/losses/ties | Exact sign p | Holm p |
|:---|---:|---:|---:|
| abc_vs_de_tuned | 11/14/0 | 0.690038 | 0.690038 |
| abc_vs_jde | 9/16/0 | 0.2295229 | 0.4590459 |

## Each of the 25 evaluation functions: 10-seed mean error

| Function | ABC | Tuned DE | jDE |
|:---|---:|---:|---:|
| F1 | 1.48546e+11 | 8.65028e+10 | **1.56062e+10** |
| F4 | 717.589 | 757.855 | **322.861** |
| F5 | 274.414 | **157.855** | 235.053 |
| F6 | 52.3051 | 45.0676 | **42.806** |
| F7 | 486.164 | **262.747** | 334.709 |
| F8 | 261.803 | **120.839** | 237.289 |
| F9 | 4061.26 | 6313.91 | **3625.03** |
| F11 | **265.232** | 409.309 | 829.358 |
| F12 | **1.88481e+07** | 7.85386e+08 | 1.16666e+09 |
| F13 | **23370.1** | 225869 | 2.65924e+08 |
| F14 | **282.33** | 27664.4 | 23829.1 |
| F15 | **1442.67** | 48171.1 | 1.41125e+07 |
| F16 | 2176.78 | **1028.98** | 1932.62 |
| F17 | 937.349 | **594.253** | 873.259 |
| F18 | **703.706** | 55142.8 | 1.7668e+06 |
| F19 | **186.579** | 631443 | 2.38207e+07 |
| F21 | 460.357 | **351.63** | 429.595 |
| F22 | 6408.03 | 3914.58 | **3137.51** |
| F23 | 683.317 | **589.232** | 589.248 |
| F24 | 740.426 | **626.272** | 652.511 |
| F25 | 713.219 | 653.381 | **600.819** |
| F26 | 4457.4 | 3604.79 | **3511.94** |
| F27 | **560.647** | 627.262 | 574.055 |
| F28 | 1052.33 | 1329.35 | **778.965** |
| F29 | 1543.85 | **1382.22** | 1744.1 |

## Methodological boundaries and negative results

- Only four development functions and three seeds per DE candidate guide a six-configuration search; the selected DE may not be robust.
- None of the 25 evaluation functions was used in **this round** of calibration, but all had already been studied in v0.13.0. Do not describe them as previously unseen functions.
- jDE is a recognized classic self-adaptive baseline, not equivalent to SHADE, L-SHADE or optimally tuned current DE implementations.
- Equal FE budgets do not imply equal wall time. Hosted runtime numbers are measured but not hardware-normalized.
- Reference backend derives from published CEC2017 C functions; it is not the organizers' official C executable.
- 10 seeds per function do not establish per-function significance; the fixed contrasts instead use function-level mean-error direction.

[Development original data](calibration_trials.csv) · [Calibration original history](calibration_history.csv) · [All six candidate ranks](calibration_candidate_ranks.csv) · [Frozen winner/metadata](calibration_selection.json) · [750 new evaluation trials](evaluation_trials.csv) · [75,000 real checkpoints](evaluation_history.csv) · [Function/method bootstraps](summary.csv) · [25-function rank records](function_ranks.csv) · [Two Holm-adjusted paired tests](function_sign_tests.csv) · [Global summaries](global_statistics.json) · [Exact source manifests](environment.json) · [Pre-experiment protocol](../../calibrated_de_jde_protocol.md)
