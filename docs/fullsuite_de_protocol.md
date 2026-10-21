# Pre-experiment protocol: full CEC2017 29-function cross-algorithm validation

**Recorded before execution (2026-10-21).**

## Motivation and fixed scope

Earlier work compared ABC, RE, EDBF and positional ablations mostly with selectively
inspected functions. This experiment adds a conventional independently implemented
**DE/rand/1/bin differential-evolution baseline** and covers **every one of the
29 retained CEC2017 functions**, rather than selectively choosing favorable cases.
CEC2017 excludes its original F2: the full test set is F1 and F3–F30.

This is a *new-seed full-function replication*, not the original paper's 100k-FE
evaluation, and not an independent implementation of the official C executable.
Performance of the reference-derived Python objective port is specifically scoped.

## Frozen design

- Objectives: CEC2017 F1, F3–F30, 30 dimensions.
- Three algorithms: original `abc`, deterministic `abc_reverse`, and
  **DE/rand/1/bin**. DE uses population 100, difference scaling F=0.8,
  binomial crossover CR=0.9, forced j_rand mutant coordinate, greedy
  one-to-one survivor selection, generational update, and box projection.
  DE is a valid well-known baseline, not a newly invented algorithm.
- Initial population: identical across all three algorithms for each paired
  (function, repeat), using `np.random.default_rng(seed)` and
  `OptimizationProblem.sample_uniform(rng, 100)`.
- New cohort: exactly **five distinct seed IDs** per function:
  `20261021 + 10000*function_id + repeat`, `repeat=0..4`.
- Function evaluation budget: **10,000 evaluations**/trial. Exactly
  100 initial individuals + 99 × 100 evolutionary evaluations, no polishing,
  no evaluation beyond 10k; all methods must reach that budget.
- **29 × 5 × 3 = 435 genuine new trials**, 43,500 measured best-so-far
  checkpoints at FE=100,200,...,10000.
- Fixed objective backend: `tilleyd/cec2017-py` reference commit
  `424a9fa2757914c3e4cfdd8f59a268b1aeb3197f`. Objective optimum and
  function id mapping validated. All box bounds [-100,100].
- All random seeds paired on the identical initial population; later RNG
  streams naturally diverge between distinct algorithm families.

## Analysis (frozen before seeing outcomes)

1. Per-function mean, median, sample SD and paired-seed **10,000-bootstrap**
   percentile intervals for mean objective error for each method.
2. Per-function method ranks from within-function mean errors, with average
   ranks across **all 29 functions**, 29-function method wins and a
   20,000-resample **random-label permutation test** of the Friedman rank
   statistic. Block is the function; ranks do not mix scales.
3. Exploratory 29-function paired sign tests of within-function mean-error
   winner (ABC vs ABC-Reverse, ABC vs DE, ABC-Reverse vs DE); apply one Holm
   family across the three contrasts. This compares function-level direction
   of mean errors, not a high-powered per-seed significance test.
4. Raw final objective errors, original convergence histories, runtime
   observations, manifest/backend checks and exact initialization checks.
5. Data-derived SVGs: an all-29-function normalized log10 mean-error heatmap,
   rank distribution / win-count graphic, and four-function sampled 10k-FE
   convergence median ± IQR ribbons (F3/F10/F20/F30 selected **before**
   execution for visualization only).

## Integrity gates

Reject missing or duplicate function/seed/method keys, mismatched seed IDs,
inconsistent 100..10000 checkpoints, unexpected early termination, invalid
CEC objective gap, nonfinite values, inconsistent history/trial endpoints, or
different initial best objective for paired runs. Regenerate all graphics
and README sections strictly from committed originals. All tests/ruff/
cross-version CI must pass before release.

## Limitations

Five seeds/function are useful for broad coverage but insufficient for
strong claims of small per-function differences. CEC2017 functions are a
curated benchmark, **not a random sample of all optimization problems**;
the 29-function permutation inference relies on the algorithm-label
exchangeability assumption across blocks. All algorithms use the **same
function-evaluation budget**, but DE typically needs 100 evaluations
per iteration versus ABC's one, so iteration counts and runtimes are not
equalized. Timing on hosted CI is indicative, not a hardware-normalized
compute cost. Fixed F=0.8 and CR=0.9 are one conventional DE configuration,
not a tuning study or a guarantee of best possible DE performance.
