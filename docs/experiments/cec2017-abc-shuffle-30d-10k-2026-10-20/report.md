# ABC-Shuffle: coefficient order / elite-rank coupling ablation

Original ABC generates an ordered vector of constrained affine weights. The optimizer supplies elite-first ordered parents. ABC-Shuffle generates the same valid coefficient multiset, then permutes it before the offspring construction; this removes deterministic coefficient index alignment without changing the coefficients themselves.

**Mechanistic exploratory experiment, not a claim of algorithmic novelty.** F10/F16/F20/F22, D=30, 10,000 FEs, 10 new paired seeds, two methods, **80 real optimization trials**. Initial populations and budgets are identical. Extra permutation RNG use changes subsequent randomness; this is not a common-random-number coupling at every later generation.

## Mean objective error (lower is better)

| Function | ABC | ABC-Shuffle |
|:---|---:|---:|
| F10 | 7559.44 | 7678.01 |
| F16 | 1995.37 | 2177.9 |
| F20 | 1009.08 | 1061.83 |
| F22 | 5484.03 | 7523.93 |

## Matched-seed paired tests

| Function | Shuffle W/L/T | paired log1p gain | bootstrap 95% CI | Holm p |
|:---|---:|---:|:---|---:|
| F10 | 5/5/0 | -0.01619 | [-0.06656, +0.03028] | 1 |
| F16 | 4/6/0 | -0.08970 | [-0.19392, +0.00967] | 1 |
| F20 | 4/6/0 | -0.05113 | [-0.13550, +0.02967] | 1 |
| F22 | 3/7/0 | -0.54081 | [-0.98634, -0.13649] | 1 |

The positive paired log1p gain indicates that ABC-Shuffle has lower error in that seed. Rejection-free feasibility and the coefficient multiset are preserved; a single factor (coefficient position) is changed. All conclusions are exploratory because the functions were selected after earlier research and this is a small, 10-seed cohort.

[80 original trials](trials.csv) · [original convergence history](history.csv) · [summary and intervals](summary.csv) · [paired tests](paired_tests.csv) · [manifest](environment.json)
