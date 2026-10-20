# Fresh-seed CEC2017 cross-function replication (exploratory)

F3/F10/F20/F30, D=30, 10,000 objective evaluations per run, ABC/EDBF/RE, 10 **new paired random seeds** for each function. The cohort is disjoint from the earlier F16/F22 seed cohort. All 120 trials used a fixed optimizer.

Functions were selected after inspecting previous results: new seeds improve replication but this is **not a preregistered selection-blind benchmark**. The four functions do not represent a random sample of CEC2017.

## Measured final objective gaps (lower is better)

| Function | Method | Mean | Median | Std dev | Bootstrap mean 95% CI |
|:---|:---|---:|---:|---:|:---|
| F3 | ABC | 39676.8 | 39016.1 | 13359 | [31932, 47603.9] |
| F3 | EDBF | 208701 | 211050 | 35382 | [188330, 229570] |
| F3 | RE | 137013 | 134210 | 25697 | [122576, 152342] |
| F10 | ABC | 7888.77 | 7896.73 | 326.76 | [7692.59, 8074.94] |
| F10 | EDBF | 7575.24 | 7495.8 | 453.05 | [7295.47, 7836.79] |
| F10 | RE | 7501.22 | 7561.05 | 678.48 | [7097.16, 7882.29] |
| F20 | ABC | 1056.71 | 1113.55 | 192.9 | [936.657, 1161.7] |
| F20 | EDBF | 1102.81 | 1108.12 | 119.66 | [1032.6, 1173.24] |
| F20 | RE | 1089.25 | 1089.61 | 153.4 | [997.645, 1176.85] |
| F30 | ABC | 86467.4 | 32862.5 | 1.1046e+05 | [29438.5, 156687] |
| F30 | EDBF | 5.11945e+07 | 4.04458e+07 | 3.4847e+07 | [3.29355e+07, 7.37396e+07] |
| F30 | RE | 5.36284e+06 | 5.56822e+06 | 2.6897e+06 | [3.74248e+06, 6.96341e+06] |

## Paired exact sign tests

| Function | Contrast | ABC W/L/T | raw p | Holm p (8 tests) |
|:---|:---|---:|---:|---:|
| F3 | abc_vs_edbf | 10/0/0 | 0.00195312 | 0.015625 |
| F3 | abc_vs_re | 10/0/0 | 0.00195312 | 0.015625 |
| F10 | abc_vs_edbf | 2/8/0 | 0.109375 | 0.4375 |
| F10 | abc_vs_re | 3/7/0 | 0.34375 | 1 |
| F20 | abc_vs_edbf | 5/5/0 | 1 | 1 |
| F20 | abc_vs_re | 6/4/0 | 0.753906 | 1 |
| F30 | abc_vs_edbf | 10/0/0 | 0.00195312 | 0.015625 |
| F30 | abc_vs_re | 10/0/0 | 0.00195312 | 0.015625 |

The sign test measures paired direction, not a comparison of mean objective errors. Holm adjustment is limited to these eight exploratory tests; earlier research selection is not covered. Bootstrap percentile intervals are based on 10,000 paired-seed resamples.

## Original evidence

[120 trials](trials.csv) · [convergence history](history.csv) · [summary](summary.csv) · [paired tests](paired_tests.csv) · [reference commit and seed source](environment.json)
