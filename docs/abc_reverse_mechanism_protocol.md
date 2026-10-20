# ABC coefficient positional-bias experiment: ABC / Shuffle / Reverse

Protocol frozen on 2026-10-20, **before** collecting this cohort.

## Mechanistic question

The preceding 80-run ABC-vs-ABC-Shuffle study observed smaller ABC means
on four purposively selected functions, but none of the paired exact sign tests
survived Holm correction. ABC-Shuffle also consumes an additional random
permutation from the **same RNG**, altering later random draws. We therefore
introduce **ABC-Reverse**, a deterministic reversal of the *same original
coefficient vector*, which consumes **no additional random draws**.
A fixed sequence reversal exchanges which coefficient positions are assigned
to the elite-first parent slots, while preserving the complete coefficient
multiset, affine sum, bounds and one-attempt generation.

Unlike a globally random permutation, reversing positions is *not* a
uniformly randomized control. It only tests one extreme deterministic
assignment. Once populations diverge, later draws occur in different
fitness landscapes: no causal isolation is claimed.

## Frozen optimizer experiment

- CEC2017 F10, F16, F20, F22, dimension 30, same pinned C-derived Python
  reference commit `424a9fa2757914c3e4cfdd8f59a268b1aeb3197f`.
- Exactly 3 coefficient modes: `abc`, `abc_shuffle`, `abc_reverse`.
  All other optimizer hyperparameters fixed at population=100, parent
  count=15, elite parent count=5, offspring count=1 and box projection.
- 10,000 function evaluations per run; **12 newly selected, paired seeds per
  function**, `20261231 + function_id*10000 + repeat`, repeats 0–11.
- Total **144 newly computed actual optimizer runs**. Four matrix jobs with
  36 trials each. Every paired initial population and 10k-evaluation cap
  must match exactly.
- Record the full trial metrics and sampled best-so-far trace at generation
  multiples of 450, including generation zero and the final FE=10k state.
  Abort evidence publication for missing or duplicate records, changed seeds,
  nonmonotonic traces, invalid objective gaps or backend provenance mismatch.
- Outcome 1: final objective error, lower better; tabulate actual means,
  medians, standard deviations and 10,000 paired-seed bootstrap percentile
  intervals.
- Outcome 2: paired log1p-error improvement `log1p(ABC error) −
  log1p(control error)`: positive means shuffle/reverse better. Eight
  comparisons (four functions × two controls) use two-sided exact paired sign
  tests with Holm correction over this whole family.
- Per-function scientific figures plot full distribution of paired effects
  and 95% bootstrap mean uncertainty. No fabricated points.

## Coefficient positional audit

Independently, sample **50,000 actual ABC vectors** with parent count 15 and
audit RNG seed 20261232. For each position report mean, median, interquartile
range, and mean absolute weight, plus the sum of absolute weights in the
first five elite-parent slots versus the remaining ten. Draw a data-derived
position-distribution SVG. Monte Carlo samples diagnose the generator's
positional marginal distributions; they are **not optimization trials**.

## Interpretation boundaries

This is a *prospective continuation of an adaptively chosen problem subset*
(F10/F16/F20/F22), not a function-blind independent test or a full 29-function
CEC replication. Position-reversal can make outcomes better, worse or neutral.
The experiment aims to falsify or refine the rank–coefficient coupling
hypothesis, not establish a new state-of-the-art algorithm.
Comparison to earlier ten-seed shuffle cohorts is descriptive only:
new cohorts use distinct seed sets and cannot be pooled without a separate
analysis. Interpret Holm adjustment only within the eight designated tests.
