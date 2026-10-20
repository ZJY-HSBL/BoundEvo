# ABC coefficient–parent ordering ablation protocol

Frozen **before** the new optimizer ablation runs on 2026-10-20.

## Mechanistic hypothesis

ABC generates an order-dependent constrained sequence of affine coefficients.
The BoundEvo optimizer selects the best K=5 parents first and appends random
others; this leaves deterministic **coefficient-index/parent-rank coupling**
even though feasibility only requires each coefficient in [-0.5, 1.5]
and the coefficients to sum to one.

The diagnostic ABC-Shuffle method runs the original ABC generator unchanged,
then draws an RNG permutation of its full coefficient vector before applying
weights to parents. Its coefficient multiset, acceptance rate and affine sum
remain exactly the same. The experiment isolates the effect of **assigning
coefficient positions to elite-first parents**. It does not separately isolate
the extra random draws or prove a mathematical mechanism from performance alone.

## Frozen design

- CEC2017 **F10, F16, F20, F22**, D=30, pinned C-derived reference at
  `424a9fa2757914c3e4cfdd8f59a268b1aeb3197f`.
- ABC versus ABC-Shuffle, all other optimizer settings unchanged:
  population=100, parents=15, elites=5, offspring=1, domain projection.
- Fresh distinct paired seeds: `20261121 + function_id * 10000 + repeat`,
  repeat=0..9, **10 seeds × 2 methods × 4 functions = 80 real runs**.
- Budget 10,000 objective evaluations for each optimizer run; sampled
  best-so-far history every 450 generations, initial FE=100 and final FE=10k.
- Verify same initial population, finite and nonnegative objective error,
  no duplicate seeds or histories, and exact final best-so-far correspondence.
- Outcome: final objective error, paired log1p difference
  `log1p(ABC error) − log1p(ABC-Shuffle error)` (positive favors shuffle).
- Four two-sided exact paired sign tests (one per function) with Holm
  adjustment; 10,000 paired bootstrap resamples for uncertainty of means.
- Record runtime but do not conflate function-evaluation parity with
  CPU/wall-clock parity.

## Limitations

Functions were chosen after previous work. This is an **exploratory
mechanistic ablation**, not selection-blind validation, full 29-function
CEC2017 benchmarking, or evidence of first-in-world algorithmic novelty.
All 80 seeds are new relative to the previous F16/F22 and fresh-function
replication cohorts. Preserve raw data and explicit negative findings.
