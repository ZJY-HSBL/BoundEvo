# Prerecorded study: calibrated DE and self-adaptive jDE against ABC

Frozen on 2026-10-21 **before** the new calibration and evaluation runs.

## Reason for the study

BoundEvo v0.13.0 compared ABC against a single, *untuned* conventional
DE/rand/1/bin setting (F=0.8, CR=0.9) across all CEC2017 functions.
The observation is valid for that baseline and evaluation budget; it does
not establish dominance over calibrated or self-adaptive differential evolution.

This study adds (i) **DE/rand/1/bin and DE/best/1/bin calibrated using only
four development functions**, and (ii) standard **jDE self-adaptation** of
individual scale factor and crossover rate. DE and jDE are established
algorithms, not claimed innovations. For jDE see Brest et al., 2006,
"Self-adapting control parameters in differential evolution"; more
competitive history-based schemes such as SHADE/L-SHADE also exist and
remain outside the present comparison.

## Explicit function split and previously observed evidence

Development functions: **F3, F10, F20, F30** (selected deliberately across
problem classes). Evaluation functions: **the remaining 25 official retained
CEC2017 functions** (F1 and F3..F30 excluding these four). No function
will appear in both parts *of this new study*.

**Critical qualification:** all 29 functions have been observed in
v0.13.0, so these 25 are held out **from the present DE configuration
selection**, not never-seen benchmark functions across the research project.
Calibration and evaluation use fresh distinct random seed ranges.
No overall 29-function ranking is asserted for the new cohort.

## Frozen calibration algorithm and criterion

Six conventional generational DE candidates: strategies `rand1bin` and
`best1bin` crossed with parameter pairs:

- (F=0.5, CR=0.9)
- (F=0.8, CR=0.3)
- (F=0.8, CR=0.9)

Common population NP=100, box projection, conventional one-to-one greedy
selection, fixed nominal 10,000 objective evaluations. Exactly **3 seeds**
per development function and candidate; new calibration seeds:
`20262101 + 10000*function_id + repeat`, repeat 0..2.

Total **4 functions × 6 candidates × 3 seeds = 72 original calibration
optimization trials**, never used for the heldout evaluation comparison.
Select one configuration by **mean rank of its mean error across the
four development functions**, ties broken using the candidate ID in
this fixed order: rand050cr090, rand080cr030, rand080cr090,
best050cr090, best080cr030, best080cr090.
No tuning is conducted on the 25 evaluation functions.
Store all 72 calibration originals, exact seed/function identities,
candidate mean/rank tables and frozen selection criteria.

## Frozen independent-seed evaluation

Algorithms: `abc` (same v0.13.0 configuration),
`de_tuned` (one winner from the calibration set), and `jde`
(self-adaptive DE/rand/1/bin, NP=100, initial F=0.5 and CR=0.9,
tau1=tau2=0.1, F resampling in [0.1,1.0], CR in [0,1];
successful offspring inherit proposed parameters, otherwise retained).
This is conventional jDE, *not* SHADE.

For each of 25 evaluation functions at 30D, execute **10 fresh matched
seed IDs** `20262201 + 10000*function_id + repeat` with repeats 0..9,
all three methods starting from the same 100 sampled initial points.
Exactly 10,000 function evaluations per run, with full checkpoint records
at 100-FE increments through FE=10,000. This is **750 additional real
optimizer runs**, entirely separate from the 72 calibration runs.

No extra polishing, no unknown offline function calls, no DE tuning using
the evaluation partition. Both DE variants use all NP=100 population
evaluations per generation. Preserve real wall-clock runtime separately
and do not equate equal FE with equal implementation runtime.

## Prespecified inference, figures and stop conditions

Use actual per-function 10-seed mean objective errors, median, standard
deviation, reproducible 10,000 seed-bootstrap replicates (paired-seed
indices across the three algorithms), and within-function mean-error
method ranks. Produce mean rank and winner counts over the 25 evaluation
function blocks, exact two-sided sign tests for ABC vs tuned DE and ABC
vs jDE with **Holm correction over these two comparisons**, and a
20,000-permutation three-method Friedman rank test on the 25 function
blocks. Report exploratory function-level p-values in the context of
curated correlated functions, not as an inference over all conceivable
tasks. There is no extra within-function statistical significance claim.

Four original-data vector graphics:
1. all 25 evaluation functions × three methods mean-error ratio heatmap,
2. development function calibration mean-rank board, frozen winner marked,
3. rank distribution and per-function winner counts on the evaluation
   partition, and
4. actual best-so-far median/IQR convergence on F1/F12/F17/F25,
   fixed before running any new seeds.

A further scientific table reports per-method observed wall-clock time
distributions from these hosted runner jobs.

Reject partial seed coverage, conflicting original source SHA, missing
checkpoints, early termination, nonmonotonic best-so-far, error below
declared CEC optimum, different paired initial errors, malformed seed
and method codes, invalid coefficient evaluation counts, inconsistent
reported means, missing PNG/SVG charts, or failed regression/ruff tests.
Use only real original experimental data for figures and README updates.

## Limitations

- The development/evaluation function split is new, but all 29 CEC2017
  objectives were examined in previous BoundEvo releases.
- Development tuning has four function blocks and three seeds each;
  the chosen configuration can be unstable. Six-candidate search is
  limited and is not exhaustive hyperparameter optimization.
- This implementation uses a C-derived *Python reference* with pinned
  commit `424a9fa2757914c3e4cfdd8f59a268b1aeb3197f`, **not** the
  organizers' official C binary.
- jDE is a stronger *adaptive* DE control than a fixed parameter,
  but SHADE, L-SHADE, and other current competitive methods remain
  untested and must not be represented as defeated.
- Runtime from hosted CI is observational, not hardware normalized.
- No claim of algorithmic originality or superiority across all
  black-box optimization problems follows from this study.
