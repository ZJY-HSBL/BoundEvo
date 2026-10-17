# BoundEvo: independent-reference 30D CEC2017 comparison

This document reports measured numbers from GitHub Actions. It is not a complete reproduction of the source paper.

Reference-derived implementation: https://github.com/tilleyd/cec2017-py
Pinned upstream commit: 424a9fa2757914c3e4cfdd8f59a268b1aeb3197f

## Protocol

- Dimensions: 30.
- Functions: [10, 20, 22, 30].
- Methods: ABC, EDBF, RE; repeats per function: 10.
- Evaluation budget per trial, including initial population: 10000.
- N=100, M=15, K=5, L=1; bounded offspring repaired by clipping.
- Identical seed and initial population for the three methods within each pair.
- Strict objective gap check; no negative error gap is silently truncated.
- Preflight: 29 official functions in 10D and 30D; zero + 5 random points each.

## Numerical integrity preflight

- Cases tested: 58; passed: 58.

## Mean objective error (lower is better)

| Function | ABC | EDBF | RE |
|:---|---:|---:|---:|
| F10 | 7470.23 | 7501.86 | 7661.92 |
| F20 | 785.202 | 1129.8 | 1049.46 |
| F22 | 5717.56 | 7651.46 | 7300.07 |
| F30 | 188044 | 6.19322e+07 | 5.51129e+06 |

## Paired exact sign tests (exploratory)

| Function | Contrast | ABC wins | Ties | ABC losses | Two-sided p |
|:---|:---|---:|---:|---:|---:|
| F10 | abc_vs_edbf | 4 | 0 | 6 | 0.753906 |
| F10 | abc_vs_re | 5 | 1 | 4 | 1 |
| F20 | abc_vs_edbf | 10 | 0 | 0 | 0.00195312 |
| F20 | abc_vs_re | 10 | 0 | 0 | 0.00195312 |
| F22 | abc_vs_edbf | 7 | 0 | 3 | 0.34375 |
| F22 | abc_vs_re | 7 | 0 | 3 | 0.34375 |
| F30 | abc_vs_edbf | 10 | 0 | 0 | 0.00195312 |
| F30 | abc_vs_re | 10 | 0 | 0 | 0.00195312 |

The sign tests are per-function and exploratory; multiple comparisons are not corrected here. Do not interpret these p values as a family-wise significant result.

## Timing and generator efficiency

| Function | Method | Mean runtime (s) | Coefficient proposals per child |
|:---|:---|---:|---:|
| F10 | abc | 1.660 | 1.000 |
| F10 | edbf | 12.463 | 4.950 |
| F10 | re | 14.396 | 210.139 |
| F20 | abc | 2.764 | 1.000 |
| F20 | edbf | 13.586 | 4.917 |
| F20 | re | 15.493 | 208.051 |
| F22 | abc | 2.815 | 1.000 |
| F22 | edbf | 13.616 | 4.912 |
| F22 | re | 15.594 | 210.153 |
| F30 | abc | 4.815 | 1.000 |
| F30 | edbf | 15.753 | 4.946 |
| F30 | re | 17.559 | 209.350 |

## Limitations

- A pinned C-derived Python implementation is an independent cross-check, not byte-for-byte execution of the organizers' official C binaries.
- Small numbers of functions and repetitions cannot establish general superiority.
- Equal evaluation budgets do not equalize implementation overhead.
- Shared random seeds equalize initial populations, not later RNG streams.
- Differences from the opfunu pilot reflect a change of benchmark backend; the numeric values from different backends must not be pooled.
- More repetitions, validated complete 29-function coverage, and paper-matching stopping rules are needed for publication claims.
