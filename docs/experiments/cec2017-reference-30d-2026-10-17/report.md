# BoundEvo: independent-reference 30D CEC2017 comparison

This document reports measured numbers from GitHub Actions. It is not a complete reproduction of the source paper.

Reference-derived implementation: https://github.com/tilleyd/cec2017-py
Pinned upstream commit: 424a9fa2757914c3e4cfdd8f59a268b1aeb3197f

## Protocol

- Dimensions: 30.
- Functions: [1, 3, 10, 30].
- Methods: ABC, EDBF, RE; repeats per function: 10.
- Evaluation budget per trial, including initial population: 3000.
- N=100, M=15, K=5, L=1; bounded offspring repaired by clipping.
- Identical seed and initial population for the three methods within each pair.
- Strict objective gap check; no negative error gap is silently truncated.
- Preflight: 29 official functions in 10D and 30D; zero + 5 random points each.

## Numerical integrity preflight

- Cases tested: 58; passed: 58.

## Mean objective error (lower is better)

| Function | ABC | EDBF | RE |
|:---|---:|---:|---:|
| F1 | 1.74702e+11 | 7.53647e+11 | 4.03772e+11 |
| F3 | 84611.2 | 294909 | 241204 |
| F10 | 8157.73 | 8047.64 | 8174.24 |
| F30 | 4.88439e+06 | 1.26157e+09 | 3.77562e+08 |

## Paired exact sign tests (exploratory)

| Function | Contrast | ABC wins | Ties | ABC losses | Two-sided p |
|:---|:---|---:|---:|---:|---:|
| F1 | abc_vs_edbf | 10 | 0 | 0 | 0.00195312 |
| F1 | abc_vs_re | 9 | 0 | 1 | 0.0214844 |
| F3 | abc_vs_edbf | 10 | 0 | 0 | 0.00195312 |
| F3 | abc_vs_re | 10 | 0 | 0 | 0.00195312 |
| F10 | abc_vs_edbf | 5 | 1 | 4 | 1 |
| F10 | abc_vs_re | 4 | 1 | 5 | 1 |
| F30 | abc_vs_edbf | 10 | 0 | 0 | 0.00195312 |
| F30 | abc_vs_re | 10 | 0 | 0 | 0.00195312 |

The sign tests are per-function and exploratory; multiple comparisons are not corrected here. Do not interpret these p values as a family-wise significant result.

## Timing and generator efficiency

| Function | Method | Mean runtime (s) | Coefficient proposals per child |
|:---|:---|---:|---:|
| F1 | abc | 0.275 | 1.000 |
| F1 | edbf | 2.536 | 4.977 |
| F1 | re | 3.002 | 210.702 |
| F3 | abc | 0.282 | 1.000 |
| F3 | edbf | 2.504 | 4.889 |
| F3 | re | 2.985 | 209.984 |
| F10 | abc | 0.305 | 1.000 |
| F10 | edbf | 2.506 | 4.947 |
| F10 | re | 2.959 | 210.150 |
| F30 | abc | 0.958 | 1.000 |
| F30 | edbf | 3.201 | 4.933 |
| F30 | re | 3.661 | 210.480 |

## Limitations

- A pinned C-derived Python implementation is an independent cross-check, not byte-for-byte execution of the organizers' official C binaries.
- Small numbers of functions and repetitions cannot establish general superiority.
- Equal evaluation budgets do not equalize implementation overhead.
- Shared random seeds equalize initial populations, not later RNG streams.
- Differences from the opfunu pilot reflect a change of benchmark backend; the numeric values from different backends must not be pooled.
- More repetitions, validated complete 29-function coverage, and paper-matching stopping rules are needed for publication claims.
