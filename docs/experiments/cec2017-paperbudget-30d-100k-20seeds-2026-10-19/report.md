# Adaptive 20-seed matched 10k-to-100k CEC2017 study

120 actual optimizer trajectories across F16/F22 (D=30), ABC/EDBF/RE, 20 paired seeds (repeats 0–19). Seeds 0–4 are the already published 100k continuations; seeds 5–19 are further continuations of the **same** previously published 10k holdout cohort.

**Important:** the extension was designed AFTER inspecting the first five 100k results, in which F22 RE had a lower observed mean than ABC but very large seed-to-seed variance. This is an adaptive follow-up and cannot be presented as an independent preregistered confirmation.

## Measured budget progression (lower error is better)

| Function | Method | Mean 10k error | Mean 100k error | 100k bootstrap 95% CI |
|:---|:---|---:|---:|:---|
| F16 | ABC | 2050.7 | 1509.1 | [1362.9, 1640.2] |
| F16 | EDBF | 2636.3 | 2094 | [2018.6, 2161.9] |
| F16 | RE | 2391.3 | 1817.9 | [1775.1, 1863.5] |
| F22 | ABC | 5755.3 | 4900.7 | [3701.8, 6024.3] |
| F22 | EDBF | 7571.2 | 6087.9 | [5183.5, 6830.4] |
| F22 | RE | 7791.6 | 5012.8 | [3737.3, 6205.7] |

## Paired exact sign tests (4 prespecified contrasts in this extension)

| Function | Contrast | ABC W/L/T | Raw p | Holm p |
|:---|:---|---:|---:|---:|
| F16 | abc_vs_edbf | 20/0/0 | 1.90735e-06 | 7.62939e-06 |
| F16 | abc_vs_re | 18/2/0 | 0.000402451 | 0.00120735 |
| F22 | abc_vs_edbf | 12/8/0 | 0.503445 | 1 |
| F22 | abc_vs_re | 9/11/0 | 0.823803 | 1 |

## Scientific boundaries

- Reusing 20 held-out seed IDs at longer budgets does NOT create a second independent cohort; matched 10k/100k curves are repeated measurements of the same deterministic random trajectories.
- Selection of F16 and F22 followed an earlier unstable ranking; the expanded 20-seed budget analysis followed an observed 5-seed F22 reversal. All claims are exploratory and adaptive.
- Bootstrap resamples the 20 paired seed indices 10,000 times using a reproducible fixed seed. Bootstrap CIs are uncertainty estimates.
- Four two-sided sign tests use Holm multiplicity adjustment, but this family correction does not control all hypotheses explored across versions or experimental stages.
- Results are on a pinned Python reference-derived CEC2017 backend, not the official C executable, and only on two functions.

## Reproducible evidence

[120 original trial records](trials.csv) · [Full convergence history](history.csv) · [Bootstrap means](summary.csv) · [Paired Holm tests](paired_tests.csv) · [Provenance](environment.json)

