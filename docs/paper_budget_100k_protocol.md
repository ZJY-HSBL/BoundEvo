# v0.11 experimental protocol: matched 10k → 100k objective evaluations

## Motivation

The published independent 20-seed study of CEC2017 F16 and F22 found that
ABC had lower mean final objective error on both functions at **10,000
evaluations**. Earlier three-seed and ten-seed experiments sometimes had other
mean leaders. The next question is whether extending **the same deterministic
trajectories** to the 100,000-evaluation cap in the source paper changes the
relative rankings and convergence rates.

This protocol was written **before inspecting 100,000-evaluation results**.

## Controlled design

| Variable | Prespecified setting |
|:---|:---|
| Functions | Official CEC2017 F16, F22 |
| Backend | Independent reference-derived `cec2017-py` port |
| Exact upstream revision | `424a9fa2757914c3e4cfdd8f59a268b1aeb3197f` |
| Dimension | 30 |
| Methods | ABC, EDBF, RE |
| Algorithm settings | N=100, M=15, K=5, L=1 |
| Evaluation cap | 100,000 including population initialization |
| Seeds per method and function | Five paired seeds, **reusing a subset** of the prior 20-seed holdout |
| Seed calculation | `20261037 + function_id × 10000 + repeat`, repeat 0–4 |
| Actual intended trials | 2 × 3 × 5 = **30** |
| Checkpoint interval | Every 900 optimizer generations (FE100, FE10000 and FE100000 all included) |
| Historical baseline | The exact matching 10,000-FE results in the already committed F16/F22 holdout |

These are not five additional independent test seeds; they are intentional
within-seed **evaluation-budget continuations**.

## Primary questions

1. Can the first 10,000 evaluations of each 100,000-FE run reproduce the
   earlier, separately recorded 10,000-FE objective gap to numerical tolerance?
2. How does the best-so-far objective error change at 100,000 evaluations
   for each method and selected function?
3. Does the observed mean-error leader on F16 and F22 change with budget?
4. How much computation time does each method consume for the longer search?

Because the optimizer's best-so-far fitness is monotonically nonincreasing,
a reduction in absolute objective gap along the **same run** is expected and
is not itself evidence of ABC superiority. The relevant comparison is relative
performance among the three methods at identical budgets and seeds.

## Hard validity gates

The runner explicitly rejects:

- a missing or duplicate historical 10k trial record;
- differing seed, function, method, or dimension compared with the source
  10k data;
- mismatch between the 10k saved historical error and the error at the exact
  FE=10,000 checkpoint of the continuing run;
- nonfinite objectives or invalid objective-minus-optimum gaps;
- early termination before 100,000 evaluations;
- missing initial, 10k, or 100k convergence checkpoints;
- an increasing best-so-far objective error;
- absent or duplicated members of any five-seed, three-method group.

Partial trial CSVs are uploaded to the GitHub Actions artifact store on job
failure, but they **cannot** be published as the complete 30-trial dataset.

## Data publication

The Actions workflow is
[`paper-budget-100k.yml`](../.github/workflows/paper-budget-100k.yml).
Once all checks pass, commit the original trial CSV, checkpoint CSV,
experiment and platform metadata, source-aligned summary and report into

`docs/experiments/cec2017-paperbudget-30d-100k-2026-10-18/`.

The bilingual README will automatically embed a reproducible SVG convergence
plot derived from the checkpoint CSV, plus a table of actual mean errors at
10k and 100k evaluations.

## Limits

Only F16/F22 and five paired seeds are included. A 100,000-FE budget alone
does not make this a replication of all 29 paper benchmarks. The independently
ported NumPy implementation has not been proven equivalent to the organizers'
official C binary. This research is exploratory; five paired seeds cannot
support robust function-specific statistical superiority claims.
