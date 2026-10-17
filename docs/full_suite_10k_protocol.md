# BoundEvo v0.9: CEC2017 full 29-function 10,000-FE study

This protocol was specified before inspecting the new full-suite results. It
is intended to check the **generality and convergence behavior** of the three
coefficient-generation approaches, not to manufacture significant results.

## Scope and fixed settings

| Variable | Setting |
|:---|:---|
| Backend | `tilleyd/cec2017-py` reference-derived CEC2017 port |
| Fixed backend revision | `424a9fa2757914c3e4cfdd8f59a268b1aeb3197f` |
| Official CEC2017 cases | F1, F3–F30 (29 functions; official F2 omitted) |
| Dimension | D = 30 |
| Comparison groups | ABC, EDBF, RE |
| Independent initial seeds | Three per function, paired across methods |
| Base seed per trial | `20261017 + 10000 × function_id + repeat` |
| Population N / parent M / elite K / children L | 100 / 15 / 5 / 1 |
| Objective evaluations | 10,000 including 100 initialization evaluations |
| Convergence checkpoints | Every 500 generations plus initial and final |
| Total planned independent trials | 29 × 3 × 3 = **261** |
| Parallel compute | 4 deterministic nonoverlapping function shards |

All three methods within a function and repetition use the same initial RNG
seed, which yields the same initial population. Later RNG streams are *not*
identical because the coefficient generators consume random values differently.

Trial records are written after each finished run. Four Actions artifacts
separately retain raw trials, sampled best/worst objective histories, and
per-shard parameter manifests. Publishing requires complete agreement across
all four shards. Incomplete runs must not be called a 261-trial study.

## Scientific questions

1. Does ABC still have the lowest mean objective error on the majority of 29
   functions with 10,000 evaluations rather than 1,200 evaluations?
2. Which functions change their lowest-observed-mean method as budget grows?
3. For F10, F20, F22 and F30, how does the normalized mean objective-error
   trajectory evolve across 100 through 10,000 evaluations?
4. Does coefficient-generation efficiency translate into lower measured wall
   time on the specific GitHub Actions machines?

## Descriptive analysis

For each function and method, report trial mean, standard deviation, median,
mean evaluations, wall time, and attempted coefficient vectors per offspring.
Rank ABC/EDBF/RE by their *per-function mean error* and count how often each
method has the smallest mean. The rank-count chart is descriptive only.

Plot normalized mean convergence as

\[
R_{f,m}(B) =
\frac{\operatorname{mean}_{s} E_{f,m,s}(B)}
{\operatorname{mean}_{s} E_{f,m,s}(100)},
\]

where `E` denotes known-optimum objective error and `B` is the number of
function evaluations. Normalize **within the same function and method** to
avoid misleading raw-error scales.

The leadership transition matrix compares identical functions, dimensions,
methods, base seeds and benchmark implementations between the 1,200- and
10,000-evaluation studies. It should not be interpreted as a causal randomized
estimate of budget effects beyond this measured experiment.

## Exploratory statistical tests

- Friedman test across the 29 function-level triplets of method mean errors.
- Two-sided paired Wilcoxon signed-rank test on log10 per-function mean errors,
  ABC versus EDBF and ABC versus RE.
- Correct the two comparisons with Holm's procedure.

These function-level tests treat 29 functions as matched blocks. They are
**exploratory**, since the benchmark functions share construction and are not
independent random samples of real-world optimization problems. Three
independent seeds per function are insufficient to assert robust per-function
superiority. Statistical tests are not substitutes for effect sizes, full
objective-error data, and uncertainty analysis.

## Integrity gates

- Exactly 261 valid, unique `(function_id, repeat, method)` trial keys.
- Every function must appear exactly once among the four assigned shards.
- Every trial must use the budget 10,000, dimension 30, and the documented
  paired seed and pinned backend revision.
- Reported objective error must equal objective minus known optimum to the
  numerical tolerance.
- Every trial must contain an initial FE=100 checkpoint and a final FE=10,000
  checkpoint; recorded best objective must be monotone nonincreasing.
- History must contain no unknown trial keys or missing method/repetition pairs.
- All summary means must be recalculated from the original trial records.
- Both README versions and their SVG figures must be generated from these
  validated CSVs, never placeholder or guessed numbers.

## Reproduction

The 4-shard GitHub Actions experiment is configured at
[full-suite-validation.yml](../.github/workflows/full-suite-validation.yml).

Execute individual shards (after installing the pinned reference backend):

```bash
python scripts/run_full_suite_shard.py \
  --shard-index 0 \
  --shard-count 4 \
  --repeats 3 \
  --evaluations 10000 \
  --output-dir /tmp/cec2017-parts/shard-0
```

Repeat indices 1, 2, 3, then aggregate (requires `scipy`):

```bash
python scripts/merge_full_suite.py \
  --input-dir /tmp/cec2017-parts \
  --output-dir docs/experiments/cec2017-fullsuite-30d-10k-2026-10-17
python scripts/update_readme_results.py
```

**Limitations:** This experiment uses 10,000 evaluations, not the source paper's
100,000; it is not a faithful reproduction of the official organizers' C
binary, and its three-seed design is insufficient for publication-grade claims
about every individual function.
