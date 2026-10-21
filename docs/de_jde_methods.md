# Calibrated differential evolution and self-adaptive jDE

This implementation records **standard published comparator algorithms**.
It does not claim to invent a new differential evolution method.

## Why extend the v0.13.0 baseline?

The prior full-CEC experiment compared the original ABC generator to a
single *fixed and untuned* DE/rand/1/bin strategy (F=0.8, CR=0.9). It
reported compelling differences on that particular configuration but
did not rule out improvement from DE parameter selection, alternate
mutation bases or individual parameter adaptation. The new
[prospective calibration/evaluation protocol](calibrated_de_jde_protocol.md)
addresses a portion of this confound.

## Implementation contracts

All methods are box-constrained, real-valued minimizers. The comparison
keeps NP=100 sampled initial individuals and exactly 10,000 objective
evaluations per run; each method logs its actual best objective at
FE=100, 200, ..., 10,000. They all start from the *same seeded
initial population* for each function/seed, but later RNG streams need
not match across different algorithms. An equal budget of function
evaluations is **not an equal wall-clock budget**.

### Conventional DE/rand/1/bin

For the i-th target, choose three distinct indices (r1,r2,r3), all
distinct from target i. The mutant is:

```text
v_i = x_r1 + F * (x_r2 - x_r3)
```

Binomial crossover selects mutant coordinates independently with
probability CR, forcing one mutant coordinate (j_rand) even when CR=0.
After coordinate-wise box projection, a feasible trial replaces
the individual target if it is no worse under the optimizer's evaluation
ordering. Each generation reads the previous generation's population
and commits replacements together.

### DE/best/1/bin

This uses the previous population's best individual as the mutation
base and two distinct donor indices that exclude the target and best
individual:

```text
v_i = x_best + F * (x_r1 - x_r2)
```

As with DE/rand/1/bin, crossover, box projection, one-to-one greedy
selection, and the exact objective-evaluation budget are unchanged.
The best individual can also be the target; in that case the donors
are drawn from the other individuals.

### Self-adaptive jDE

The implementation follows the **individual-parameter adaptation**
principle introduced by Brest et al. (2006) rather than using a
global history archive. Each target has separate persistent Fi and
CRi, initially F=0.5, CR=0.9. Immediately before making an offspring:

```text
with probability tau1 = 0.1:
    Fi_proposed = 0.1 + 0.9 * Uniform(0,1)
otherwise:
    Fi_proposed = Fi

with probability tau2 = 0.1:
    CRi_proposed = Uniform(0,1)
otherwise:
    CRi_proposed = CRi
```

The mutation base is DE/rand/1, crossover is binomial with forced
mutant coordinate. **Proposed control values are inherited only if
the challenger survives greedy selection**. Failed proposals leave
Fi and CRi unchanged. There is no separate hidden evaluation for
adaptation.

Canonical reference: Brest, Greiner, Bošković, Mernik & Žumer,
"Self-Adapting Control Parameters in Differential Evolution:
A Comparative Study on Numerical Benchmark Problems,"
IEEE Transactions on Evolutionary Computation 10(6), 646–657
(2006), DOI: [10.1109/TEVC.2006.872133](https://doi.org/10.1109/TEVC.2006.872133).

## Deliberate limitations

A self-adaptive jDE control is stronger than claiming one untuned
fixed DE setting is representative of all DE variants, but it is not
SHADE or L-SHADE. SHADE uses a separate *success-history memory*
of control parameter settings:
Tanabe & Fukunaga, "Success-History Based Parameter Adaptation for
Differential Evolution," IEEE CEC 2013,
DOI: [10.1109/CEC.2013.6557555](https://doi.org/10.1109/CEC.2013.6557555).

The current design searches only six conventional DE configurations
and selects on four previously observed development functions. Its
25 evaluation functions are **untouched by the selection procedure in
this round, but not unobserved in the BoundEvo research history**.
The calibration uses three seeds/function and the evaluation uses ten,
so the chosen model can be unstable. Full black-box benchmarking,
for example with the COCO platform
([Hansen et al., 2016](https://arxiv.org/abs/1603.08785)),
remains a separate future validation direction.
