# BoundEvo algorithm notes

BoundEvo implements a real-coded, elite-preserving multi-parent evolutionary optimizer and three reference coefficient-vector generators: random exhaustive (RE), empirical-distribution based (EDBF), and adaptive boundary constraint (ABC), plus a separate ABC-Shuffle mechanism ablation.

## Coefficient constraints

For `M` parents, a recombination vector must satisfy

\[
\sum_{i=1}^{M}\alpha_i=1, \qquad -0.5\le\alpha_i\le1.5.
\]

The offspring is the affine combination

\[
x'=\sum_{i=1}^{M}\alpha_i x_i.
\]

## Adaptive boundary generation

Let `s` be the sum of coefficients already chosen. For each of the first `M-1` coefficients, choose

\[
\alpha_i\sim U\left(\max(-0.5-s,-0.5),\;\min(1.5-s,1.5)\right)
\]

and update `s <- s + alpha_i`. Then set

\[
\alpha_M=1-s.
\]

Because every update keeps `s` inside `[-0.5,1.5]`, the final coefficient is automatically inside `[-0.5,1.5]`. No rejection loop is needed.

The source flowchart prints a stopping test around `i == M-1` while also labeling the computed final value as `alpha_M`. Taken literally, that would leave one coefficient missing. BoundEvo uses the mathematically consistent interpretation: randomly generate exactly `M-1` coefficients, then compute the `M`-th coefficient from the sum constraint. This also matches the stated `M`-component coefficient vector.

## Population update

1. Initialize `N` points uniformly in the box domain.
2. Rank individuals by total inequality-constraint violation, then by objective value.
3. Select the best `K` individuals and sample `M-K` additional parents from the remainder.
4. Generate `L` children by multi-parent affine recombination.
5. Keep the best child and replace the current worst individual if the child is no worse.
6. Repeat until the population converges numerically or the evaluation budget is exhausted.

Offspring outside the variable box are projected back to the box. This explicit repair policy is an implementation choice because the affine subspace can otherwise leave the bounded search domain.

## ABC-Shuffle: coefficient-position / parent-rank coupling

Selected parents are ordered as K elite individuals, followed by M-K
randomly sampled non-elites. Original ABC constructs coefficients sequentially
and does **not** permute coefficient positions. Thus coefficient index can
interact with the elite-first rank ordering.

The diagnostic `abc_shuffle` mode generates the original ABC coefficient
vector, then draws an independent random permutation of its coordinates.
The **coefficient multiset**, affine sum of one, coordinate bounds [-0.5, 1.5],
and rejection-free one-attempt generation remain exactly conserved.
Only the coefficient-to-parent positional mapping changes. The permutation
also consumes RNG draws, so subsequent random streams can differ.

This is an **exploratory mechanism ablation**, not a proven new optimizer.
The [frozen study design](abc_shuffle_ablation_protocol.md) and
[80 measured optimization runs](experiments/cec2017-abc-shuffle-30d-10k-2026-10-20/report.md)
find that ABC has lower observed mean error than ABC-Shuffle on F10/F16/F20/F22
at 10k function evaluations and 10 fresh paired seeds/function, but **none
of the four paired sign tests were significant after Holm adjustment**.
The rank-coupling hypothesis remains unconfirmed.

## Research interpretation

The separately published [120 fresh-seed cross-function trials](experiments/cec2017-fresh-functions-30d-10k-2026-10-20/report.md)
show function-dependent ranking: ABC has lowest observed mean on F3/F20/F30
whereas RE leads on F10, without Holm-significant F10 pairwise evidence.
[Whole-trajectory anytime analysis](experiments/cec2017-anytime-30d-100k-20seeds-2026-10-20/report.md)
also shows that endpoint rankings need not imply whole-trajectory statistical
superiority. Function and long-budget analyses were selected adaptively, so
these remain exploratory rather than independent universal validation.

## ABC-Reverse: deterministic position control without additional RNG draws

The `abc_reverse` coefficient-generation option draws the same valid ABC
vector as unmodified ABC and returns the vector in **reversed index order**.
For fixed parent count and RNG state, coefficient values are exactly
preserved and the generator consumes **no additional random samples**.
This is verified by unit tests comparing both the exact reversed vector
and the next RNG output after the call.

The original `abc_shuffle` permutes coefficients stochastically and therefore
consumes additional RNG draws. Comparing ABC, ABC-Shuffle and ABC-Reverse
helps distinguish a possible coefficient-index assignment effect from the
extra RNG use in the earlier random-shuffle ablation.

The [frozen three-arm protocol](abc_reverse_mechanism_protocol.md) tested
F10/F16/F20/F22 with 12 previously unused paired seeds per function,
three methods and 10k FE: **144 additional real optimizer runs**.
[Full original results](experiments/cec2017-abc-reverse-30d-10k-2026-10-20/report.md)
showed ABC-Reverse with larger mean error than ABC on all four functions.
**None of eight exact paired sign tests survived Holm correction**.
The experiment is therefore an exploratory mechanism probe, not proof
of superiority or an established causal mechanism.

A separate Monte Carlo diagnostic generated **50,000 valid ABC coefficient
vectors** at parent count M=15. The first K=5 elite-aligned coefficient
slots received an average **42.23%** of the within-vector absolute
coefficient mass, compared with 33.33% of total coefficient positions.
This is a descriptive positional distribution difference; it does not
establish the optimizer's performance effect or generalizability.
