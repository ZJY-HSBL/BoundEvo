# Independent fresh-seed holdout: CEC2017 F16 and F22

## Protocol

- D=30, 10,000 function evaluations including N=100 initialization.
- F16 and F22, three methods ABC/EDBF/RE.
- Twenty **new** independent seeds per method/function: 20261037 + 10,000 × function ID + repeat, repeat 0..19.
- The seed range is disjoint from the previously published seeds at base 20261017 with repeat IDs 0..9.
- 120 measured optimization trials. Matched initialization within each repeat.
- Benchmark backend: independent C-derived Python port at revision 424a9fa2757914c3e4cfdd8f59a268b1aeb3197f.
- Confidence intervals: 10,000 paired bootstrap resamples, fixed seed 20261017 + function ID, percentile 95% intervals.
- Exact two-sided paired sign tests; Holm correction over four contrasts.

## Measured means with percentile bootstrap 95% CI

| Function | Method | Mean objective error | 95% CI for mean error |
|:---|:---|---:|:---|
| F16 | ABC | 2050.72 | [1934.38, 2172.81] |
| F16 | EDBF | 2636.26 | [2548.62, 2715.47] |
| F16 | RE | 2391.32 | [2296.2, 2471.84] |
| F22 | ABC | 5755.32 | [4391.98, 7056.59] |
| F22 | EDBF | 7571.17 | [7137.03, 7890.04] |
| F22 | RE | 7791.64 | [7395.54, 8097.78] |

## Matched comparisons (ABC versus baselines)

| Function | Contrast | ABC W/L/T | Raw p | Holm p | Paired log1p difference (95% CI) |
|:---|:---|---:|---:|---:|:---|
| F16 | abc_vs_edbf | 19/1/0 | 4.00543e-05 | 0.000160217 | +0.25725 [+0.18357, +0.3276] |
| F16 | abc_vs_re | 16/4/0 | 0.0118179 | 0.0354538 | +0.15866 [+0.071096, +0.2398] |
| F22 | abc_vs_edbf | 13/7/0 | 0.263176 | 0.263176 | +0.56518 [+0.17606, +0.99838] |
| F22 | abc_vs_re | 14/6/0 | 0.115318 | 0.230637 | +0.59576 [+0.20456, +1.0268] |

## Interpretation limits

- This is a **holdout** cohort chosen after prior F16/F22 sensitivity was detected; the listed seeds themselves were not included in the prior experiments.
- Bootstrap confidence intervals use ordinary empirical resampling of 20 matched seed indices; they are estimates, not exact coverage guarantees.
- The sign test conditions on non-tied pairs; Holm controls the tested four-contrast family, not every benchmark hypothesis considered previously.
- The paired log1p advantage is positive if ABC tends to produce smaller objective gaps on the same seeds.
- F16/F22 were selected for ambiguity. These results cannot establish general optimization superiority across all CEC2017 functions.
- Running times depend on the Python implementation and GitHub runner.
- The fixed reference-derived Python CEC2017 implementation is not the organizers' original C binary.

## Source data

[120 measured trial rows](trials.csv) · [method-level summary and bootstrap CI](summary.csv) · [Holm-adjusted paired comparisons](paired_tests.csv) · [runtime provenance](environment.json)
