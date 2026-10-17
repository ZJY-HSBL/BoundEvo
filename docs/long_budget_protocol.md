# CEC2017 focused longer-budget replication protocol

This is an **experimental extension**, not a claim of complete source-paper
replication. The purpose is to challenge earlier short-budget findings instead
of running only functions where the ABC generator already wins.

## Why these four functions?

In the [29-function, D=30 screening](experiments/cec2017-screen-30d-2026-10-17/statistical_analysis_CN.md),
ABC had the lowest observed mean error on 27 of 29 cases at **1,200 evaluations**,
but **RE was lower on F20 and F22**. In the independent
[3,000-evaluation, 10-seed experiment](experiments/cec2017-reference-30d-2026-10-17/statistical_analysis_CN.md),
**EDBF** was slightly lower than ABC on F10. F30 was included as a complex
composition-function positive control.

The new selected-function protocol therefore uses **F10, F20, F22 and F30**
instead of sampling exclusively from ABC-favorable problems. It must not be
summarized as a complete CEC2017 result.

## Fixed experimental design

| Parameter | Setting |
|:---|:---|
| CEC2017 backend | Independent reference-derived `cec2017-py` |
| Backend source revision | `424a9fa2757914c3e4cfdd8f59a268b1aeb3197f` |
| Official functions | F10, F20, F22, F30 |
| Dimension | 30 |
| Methods | ABC, EDBF, RE |
| Independent initial seeds | 10 per function, matched across methods |
| Population N | 100 |
| Parent count M | 15 |
| Elite parent count K | 5 |
| Offspring count L | 1 |
| Function evaluations | **10,000 per trial**, including N=100 initialization |
| Intended completed runs | **4 × 3 × 10 = 120** |
| Prior common-budget comparison | F10 and F30 at 3,000 evaluations with the same seed schedule |

Each method uses the same seed for a function-and-repeat pair to reproduce
the same initial population. The subsequent RNG streams diverge because the
coefficient-generation algorithms consume random numbers differently.

All trial records must pass finite objective-gap, strict function-evaluation
budget, finite runtime, and seed-pairing checks. The workflow preflights all 29
official CEC2017 functions at both D=10 and D=30.

The independent benchmark code is adapted from the published C implementation,
but has not been proven identical to the organizers' official C binary.

## Expected reproducible artifacts

Once the workflow succeeds, data are committed to
`docs/experiments/cec2017-longbudget-30d-2026-10-17/`:

- `trials.csv`: all 120 raw trial records;
- `summary.csv`: method-level means, standard deviations, runtime, evaluation
  counts, and coefficient-generation attempts;
- `paired_sign_tests.csv`: exploratory paired exact sign tests;
- `backend_preflight.csv`: sampled-point validity checks;
- `environment.json`: full runtime, fixed repository revision, backend source
  revision, evaluation budget and seed policy;
- `report.md`: detailed source-aligned protocol and measurement summary.

The data, summary tables, and a new SVG error-comparison chart are added to
both `README.md` and `README_CN.md` automatically after validation.

## Interpretation

An error improvement at 1,200 evaluations is not automatically persistent at
10,000 or 100,000 evaluations. Results with unequal evaluation budgets must
appear in separate cohorts, even when overlapping functions are plotted.

F10 and F30 at 3,000 evaluations may be compared descriptively to the 10,000
evaluation data because they use the same benchmark backend, dimension and
seed schedule. The remaining F20 and F22 are newly tested at the higher budget
and cannot be compared to 3,000-evaluation records that do not exist.

With 10 independent seeds per problem, exact paired tests have limited power,
particularly after adjustment for eight function/method contrasts.
Statistical significance claims must not be generalized to the 29-function
suite. Results are exploratory; follow-up should include the entire suite at
higher budgets, additional seeds, uncertainty intervals, and sensitivity to
the original paper's stopping rule.
