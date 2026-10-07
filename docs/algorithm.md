# BoundEvo algorithm notes

BoundEvo implements a real-coded, elite-preserving multi-parent evolutionary optimizer and three coefficient-vector generators: random exhaustive (RE), empirical-distribution based (EDBF), and adaptive boundary constraint (ABC).

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
