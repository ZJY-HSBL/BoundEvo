# BoundEvo: independent-reference 30D CEC2017 comparison

This document reports measured numbers from GitHub Actions. It is not a complete reproduction of the source paper.

Reference-derived implementation: https://github.com/tilleyd/cec2017-py
Pinned upstream commit: 424a9fa2757914c3e4cfdd8f59a268b1aeb3197f

## Protocol

- Dimensions: 30.
- Functions: [1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30].
- Methods: ABC, EDBF, RE; repeats per function: 3.
- Evaluation budget per trial, including initial population: 1200.
- N=100, M=15, K=5, L=1; bounded offspring repaired by clipping.
- Identical seed and initial population for the three methods within each pair.
- Strict objective gap check; no negative error gap is silently truncated.
- Preflight: 29 official functions in 10D and 30D; zero + 5 random points each.

## Numerical integrity preflight

- Cases tested: 58; passed: 58.

## Mean objective error (lower is better)

| Function | ABC | EDBF | RE |
|:---|---:|---:|---:|
| F1 | 3.1105e+11 | 1.15555e+12 | 7.78444e+11 |
| F3 | 177415 | 322831 | 364142 |
| F4 | 6418.82 | 23820.3 | 17157.1 |
| F5 | 380.096 | 604.074 | 494.383 |
| F6 | 91.8996 | 155.473 | 137.636 |
| F7 | 1059.05 | 2393.07 | 2132.81 |
| F8 | 373.616 | 526.764 | 514.199 |
| F9 | 14678.9 | 31282.9 | 25991 |
| F10 | 8590.07 | 8961.34 | 8594.21 |
| F11 | 2457.3 | 20970.9 | 14172.1 |
| F12 | 8.5343e+09 | 8.60785e+10 | 4.63511e+10 |
| F13 | 2.84921e+09 | 5.18455e+10 | 3.08306e+10 |
| F14 | 90796 | 4.43239e+06 | 1.93249e+06 |
| F15 | 2.54625e+08 | 5.54596e+09 | 2.83998e+09 |
| F16 | 2871.27 | 3246.99 | 3338.95 |
| F17 | 1476.65 | 2315.5 | 1874.27 |
| F18 | 6.37086e+06 | 7.38529e+07 | 2.40566e+07 |
| F19 | 3.75201e+08 | 1.44052e+10 | 4.28378e+09 |
| F20 | 1410.78 | 1392.03 | 1338.99 |
| F21 | 544.967 | 724.289 | 640.611 |
| F22 | 8534.33 | 8756.71 | 8350.95 |
| F23 | 853.651 | 1089.72 | 960.42 |
| F24 | 911.882 | 1120.33 | 986.663 |
| F25 | 2313.92 | 11118.9 | 5975.97 |
| F26 | 5683.03 | 8455.97 | 7567.1 |
| F27 | 718.924 | 875.717 | 878.46 |
| F28 | 2782.38 | 6010.56 | 5059.34 |
| F29 | 1999.87 | 2541.58 | 2910.14 |
| F30 | 2.69429e+08 | 4.47845e+09 | 3.94286e+09 |

## Paired exact sign tests (exploratory)

| Function | Contrast | ABC wins | Ties | ABC losses | Two-sided p |
|:---|:---|---:|---:|---:|---:|
| F1 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F1 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F3 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F3 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F4 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F4 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F5 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F5 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F6 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F6 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F7 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F7 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F8 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F8 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F9 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F9 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F10 | abc_vs_edbf | 2 | 1 | 0 | 0.5 |
| F10 | abc_vs_re | 1 | 1 | 1 | 1 |
| F11 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F11 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F12 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F12 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F13 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F13 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F14 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F14 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F15 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F15 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F16 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F16 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F17 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F17 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F18 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F18 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F19 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F19 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F20 | abc_vs_edbf | 0 | 1 | 2 | 0.5 |
| F20 | abc_vs_re | 1 | 0 | 2 | 1 |
| F21 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F21 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F22 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F22 | abc_vs_re | 0 | 0 | 3 | 0.25 |
| F23 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F23 | abc_vs_re | 2 | 0 | 1 | 1 |
| F24 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F24 | abc_vs_re | 2 | 0 | 1 | 1 |
| F25 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F25 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F26 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F26 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F27 | abc_vs_edbf | 2 | 0 | 1 | 1 |
| F27 | abc_vs_re | 2 | 0 | 1 | 1 |
| F28 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F28 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F29 | abc_vs_edbf | 2 | 0 | 1 | 1 |
| F29 | abc_vs_re | 3 | 0 | 0 | 0.25 |
| F30 | abc_vs_edbf | 3 | 0 | 0 | 0.25 |
| F30 | abc_vs_re | 3 | 0 | 0 | 0.25 |

The sign tests are per-function and exploratory; multiple comparisons are not corrected here. Do not interpret these p values as a family-wise significant result.

## Timing and generator efficiency

| Function | Method | Mean runtime (s) | Coefficient proposals per child |
|:---|:---|---:|---:|
| F1 | abc | 0.167 | 1.000 |
| F1 | edbf | 1.367 | 4.932 |
| F1 | re | 1.563 | 209.619 |
| F3 | abc | 0.178 | 1.000 |
| F3 | edbf | 1.376 | 4.887 |
| F3 | re | 1.645 | 216.554 |
| F4 | abc | 0.170 | 1.000 |
| F4 | edbf | 1.368 | 4.915 |
| F4 | re | 1.597 | 213.544 |
| F5 | abc | 0.167 | 1.000 |
| F5 | edbf | 1.358 | 4.850 |
| F5 | re | 1.561 | 208.328 |
| F6 | abc | 0.173 | 1.000 |
| F6 | edbf | 1.396 | 4.975 |
| F6 | re | 1.594 | 212.385 |
| F7 | abc | 0.199 | 1.000 |
| F7 | edbf | 1.432 | 5.002 |
| F7 | re | 1.658 | 218.637 |
| F8 | abc | 0.179 | 1.000 |
| F8 | edbf | 1.408 | 4.994 |
| F8 | re | 1.592 | 212.494 |
| F9 | abc | 0.183 | 1.000 |
| F9 | edbf | 1.387 | 4.931 |
| F9 | re | 1.570 | 207.667 |
| F10 | abc | 0.191 | 1.000 |
| F10 | edbf | 1.418 | 5.011 |
| F10 | re | 1.611 | 212.656 |
| F11 | abc | 0.226 | 1.000 |
| F11 | edbf | 1.466 | 5.043 |
| F11 | re | 1.629 | 209.265 |
| F12 | abc | 0.242 | 1.000 |
| F12 | edbf | 1.418 | 4.797 |
| F12 | re | 1.648 | 208.250 |
| F13 | abc | 0.245 | 1.000 |
| F13 | edbf | 1.431 | 4.842 |
| F13 | re | 1.637 | 206.930 |
| F14 | abc | 0.244 | 1.000 |
| F14 | edbf | 1.469 | 4.992 |
| F14 | re | 1.641 | 207.271 |
| F15 | abc | 0.233 | 1.000 |
| F15 | edbf | 1.425 | 4.855 |
| F15 | re | 1.662 | 211.460 |
| F16 | abc | 0.262 | 1.000 |
| F16 | edbf | 1.448 | 4.837 |
| F16 | re | 1.680 | 210.514 |
| F17 | abc | 0.315 | 1.000 |
| F17 | edbf | 1.512 | 4.873 |
| F17 | re | 1.720 | 208.309 |
| F18 | abc | 0.252 | 1.000 |
| F18 | edbf | 1.421 | 4.785 |
| F18 | re | 1.660 | 209.428 |
| F19 | abc | 0.290 | 1.000 |
| F19 | edbf | 1.499 | 4.946 |
| F19 | re | 1.706 | 209.877 |
| F20 | abc | 0.318 | 1.000 |
| F20 | edbf | 1.520 | 4.892 |
| F20 | re | 1.700 | 204.990 |
| F21 | abc | 0.297 | 1.000 |
| F21 | edbf | 1.529 | 5.012 |
| F21 | re | 1.701 | 208.659 |
| F22 | abc | 0.325 | 1.000 |
| F22 | edbf | 1.548 | 4.978 |
| F22 | re | 1.730 | 209.338 |
| F23 | abc | 0.359 | 1.000 |
| F23 | edbf | 1.588 | 4.988 |
| F23 | re | 1.748 | 206.642 |
| F24 | abc | 0.348 | 1.000 |
| F24 | edbf | 1.559 | 4.930 |
| F24 | re | 1.760 | 209.124 |
| F25 | abc | 0.371 | 1.000 |
| F25 | edbf | 1.559 | 4.889 |
| F25 | re | 1.800 | 213.629 |
| F26 | abc | 0.401 | 1.000 |
| F26 | edbf | 1.635 | 5.039 |
| F26 | re | 1.837 | 213.679 |
| F27 | abc | 0.431 | 1.000 |
| F27 | edbf | 1.610 | 4.827 |
| F27 | re | 1.832 | 208.581 |
| F28 | abc | 0.425 | 1.000 |
| F28 | edbf | 1.647 | 4.992 |
| F28 | re | 1.812 | 206.897 |
| F29 | abc | 0.595 | 1.000 |
| F29 | edbf | 1.852 | 5.069 |
| F29 | re | 2.000 | 208.529 |
| F30 | abc | 0.559 | 1.000 |
| F30 | edbf | 1.741 | 4.814 |
| F30 | re | 2.019 | 216.031 |

## Limitations

- A pinned C-derived Python implementation is an independent cross-check, not byte-for-byte execution of the organizers' official C binaries.
- Small numbers of functions and repetitions cannot establish general superiority.
- Equal evaluation budgets do not equalize implementation overhead.
- Shared random seeds equalize initial populations, not later RNG streams.
- Differences from the opfunu pilot reflect a change of benchmark backend; the numeric values from different backends must not be pooled.
- More repetitions, validated complete 29-function coverage, and paper-matching stopping rules are needed for publication claims.
