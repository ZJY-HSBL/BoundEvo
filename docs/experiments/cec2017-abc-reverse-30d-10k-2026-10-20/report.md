# ABC coefficient position: 144-trial three-arm mechanism study

This prerecording-followed exploratory experiment runs the unmodified ABC generator, stochastic ABC-Shuffle and deterministic **ABC-Reverse**. Reversal consumes **zero additional random draws** while preserving the exact original ABC coefficient multiset, affine sum and validity. The new 12-seed cohort is independent of previous cohorts, but the four functions were selected adaptively after earlier results.

## Mean final objective error (lower is better)

| Function | ABC | ABC-Shuffle | ABC-Reverse |
|:---|---:|---:|---:|
| F10 | 7,701.725 | 7,504.495 | 7,965.946 |
| F16 | 2,097.114 | 2,133.387 | 2,372.106 |
| F20 | 965.086 | 989.040 | 1,062.085 |
| F22 | 6,006.285 | 6,503.669 | 8,064.009 |

## Eight paired exact sign tests (all Holm-adjusted together)

| Function | Positional control | Control W/L/T | Mean paired log1p gain | 95% paired bootstrap CI | Holm p |
|:---|:---|---:|---:|:---|---:|
| F10 | abc_shuffle_vs_abc | 7/5/0 | +0.0298 | [-0.0265, +0.0918] | 1 |
| F10 | abc_reverse_vs_abc | 6/6/0 | -0.0344 | [-0.0688, -0.0023] | 1 |
| F16 | abc_shuffle_vs_abc | 6/6/0 | -0.0235 | [-0.0889, +0.0434] | 1 |
| F16 | abc_reverse_vs_abc | 2/10/0 | -0.1278 | [-0.2275, -0.0312] | 0.30859 |
| F20 | abc_shuffle_vs_abc | 5/7/0 | -0.0265 | [-0.0997, +0.0427] | 1 |
| F20 | abc_reverse_vs_abc | 2/10/0 | -0.1034 | [-0.2353, +0.0060] | 0.30859 |
| F22 | abc_shuffle_vs_abc | 4/8/0 | -0.2012 | [-0.5839, +0.0610] | 1 |
| F22 | abc_reverse_vs_abc | 3/9/0 | -0.5341 | [-1.0512, -0.0840] | 0.87598 |

Positive paired log1p gain means the positional control has lower error than ABC. Exact sign tests quantify the direction of the paired outcome, not directly the mean-error comparison. Multiple testing outside this eight-comparison family is not controlled.

## Generator-level positional distribution audit (not optimizer runs)

Generated 50,000 independent valid ABC coefficient vectors at M=15, using audit seed 20261232. The first five elite-assigned positions carry on average 42.23% of total absolute coefficient mass. A position-specific sampling distribution is consistent with the potential rank-coupling mechanism, but neither the coefficient statistic nor the optimizer ablation alone proves a causal benefit.

## Scientific limitations

- The functions are an adaptively selected CEC2017 subset, not all 29 functions.
- ABC-Reverse is a deterministic extreme order assignment, not a random permutation test. It avoids ABC-Shuffle's extra RNG draws but does not hold later populations or coefficient draws identical after trajectories diverge.
- Each method has the same population, fresh paired initial seeds, and 10k function-evaluation budget. Wall-clock compute cost is separately observed.
- The fixed C-derived Python reference backend is not the organizer's official C executable. Do not claim general algorithm dominance.

## Original data and figures

[144 original optimizer trials](trials.csv) · [3,312 convergence records](history.csv) · [12 method summaries](summary.csv) · [eight Holm contrasts](paired_tests.csv) · [all per-seed paired effects](paired_effects.csv) · [50,000-draw generator marginal diagnostics](coefficient_position_audit.csv) · [coefficient audit overview](coefficient_audit.json) · [frozen protocol](../../abc_reverse_mechanism_protocol.md)
