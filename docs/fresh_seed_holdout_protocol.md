# v0.10.0: independent fresh-seed robustness study

The earlier [full-suite study](full_suite_10k_protocol.md) contained three
paired seeds per function. Its D=30, 10,000-evaluation mean-error leaders were
RE on F16 and EDBF on F22, while an earlier **ten-seed** F22 study had ABC
as its observed leader. Those conflicting rankings motivated this new
independent-seed evaluation.

## Prespecified experimental design

| Property | Prespecified setting |
|:---|:---|
| Functions | **F16 and F22 only**, selected for uncertain method ranking |
| Dimensions | D=30 |
| Methods | ABC, EDBF, RE |
| Budget | 10,000 function evaluations per run (N=100 initialization included) |
| Population / parent / elite / offspring | N=100, M=15, K=5, L=1 |
| **New independent seeds** | 20 per method and function |
| Base seed | `20261037` |
| Actual seed | `20261037 + function_id × 10000 + repeat`, repeat 0..19 |
| Previously used seeds | Base `20261017`, repeat 0..9 (no overlap) |
| Completed optimization trials | 2 functions × 20 seeds × 3 methods = **120** |
| Benchmark backend | `tilleyd/cec2017-py`, pinned at `424a9fa2757914c3e4cfdd8f59a268b1aeb3197f` |
| Seed pairing | Same initial seed across three coefficient generators |
| CI method | Seed-resampling percentile bootstrap, 10,000 resamples, fixed RNG |
| Paired tests | Exact two-sided sign tests, jointly Holm-adjusted for 4 contrasts |

The seed set is **disjoint** from the previous ten-seed F22 experiment and
three-seed F16/F22 experiments. This avoids counting already observed seeds
again when judging these selected cases.

## Primary interpretation

Each function is reported separately. The first comparison is the **observed
mean objective error** and its 95% percentile bootstrap interval based on 20
fresh seeds. To assess paired differences, calculate

\[
d_s = \log(1+E_{\mathrm{baseline},s})
- \log(1+E_{\mathrm{ABC},s}),
\]

where positive values favor ABC. Report its mean and the paired-bootstrap
95% interval, with matched seed indices resampled together.

Additionally, report the number of ABC paired wins, losses and ties
and a two-sided exact sign-test p value. Use the Holm procedure across the
four prespecified comparisons:

- F16: ABC vs EDBF
- F16: ABC vs RE
- F22: ABC vs EDBF
- F22: ABC vs RE

Neither point-estimate leadership nor bootstrap interval overlap alone should
be treated as an automatic binary significance test.

## Data integrity requirements

The data merger must verify: correct pinned benchmark revision; **58/58**
backend numerical preflight checks per function worker; exactly 60 trials per
function; 20 unique paired seeds for every method; all 120 trials at D=30 and
10,000 objective evaluations; finite errors equal objective minus declared
optimum; complete raw CSV and reproducibility manifests. **Incomplete or
corrupted runs are not reported as finished data.**

## Artifacts and figures

The Actions workflow [holdout-seeds.yml](../.github/workflows/holdout-seeds.yml)
runs F16 and F22 independently, then merges the two experimental cohorts.
Only after integrity checks pass do `trials.csv`, `summary.csv`,
`paired_tests.csv`, `environment.json` and `report.md` get committed
in `docs/experiments/cec2017-holdout-30d-10k-2026-10-17/`.

Both README versions embed the generated
`docs/figures/cec2017-f16-f22-holdout-mean-errors.svg`
from the actual CSV. No decorative or simulated empirical figures are used.

## Limitations

These two functions were selected after observing earlier results, so the
selection process was not blind. Fresh seeds address seed reuse, not selection
bias or generalization to all optimization problems. The reference-derived
Python backend is not the competition organizers' original C binary, and
10,000 function evaluations are fewer than the source paper's 100,000.
