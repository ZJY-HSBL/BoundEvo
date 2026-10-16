# CEC2017 reproduction protocol

This repository separates settings stated by the source material from implementation choices needed to make the experiment executable.

## Source-aligned settings

The main comparison uses:

- population size `N = 100`;
- parent count `M = 15`;
- elite-parent count `K = 5`;
- offspring count `L = 1`;
- 29 CEC2017 functions: `F1` and `F3` through `F30`;
- best objective, runtime, and function-evaluation count as principal metrics.

The source also reports parameter sweeps for `M = 10..16` on `F1`, `F10`, `F20`, and `F30`.

## Explicit implementation choices

The extracted source text does not state benchmark dimensionality in its experiment-settings paragraph. Therefore `scripts/run_cec2017.py` exposes `--dimension`; the default value `10` is a convenience setting, not a claim about the source experiment.

CEC2017 functions, shifts, rotations, bounds, and known optima are supplied by the optional `opfunu` dependency instead of being copied into this repository. BoundEvo reads `lb`, `ub`, `f_global`, and `evaluate()` from each benchmark object.

The optimizer uses the same parent-selection and population-update logic for RE, EDBF, and ABC, changing only the coefficient generator.

## Numerical integrity warning (October 2026)

The upstream `opfunu==1.0.1` library renumbers the CEC2017 functions
F1 and F3..F30 to classes F1..F29. The adapter now maps the official IDs
and explicitly supplies corresponding shifts, rotations, and objective biases.

**Mapping correctness is not sufficient to guarantee numerical correctness.**
A live pilot detected results below the benchmark's claimed F10 global optimum
and nonfinite values on F30 at a preflight point. Both are excluded from the
validated pilot. These findings are tracked in
[issue #3](https://github.com/ZJY-HSBL/BoundEvo/issues/3).

The actual validated 60-trial pilot covers F1, F3, F5, and F20, with five
matched initial seeds per method and 1500 evaluations per trial. See
[validation_readme.md](experiments/cec2017-pilot-2026-10-17/validation_readme.md)
and the accompanying raw CSVs.

Until the remaining benchmark functions are verified against an authoritative
CEC2017 reference implementation, do **not** represent the full 29-function
experiment as a numerical reproduction of the source paper.

## Run the 29-function matrix (experimental, not yet validated)

```bash
pip install -e ".[cec2017]"
python scripts/run_cec2017.py --dimension 10 --repeats 1
```

For a more meaningful stochastic comparison:

```bash
python scripts/run_cec2017.py --dimension 10 --repeats 30
```

Outputs:

- `results/cec2017_trials.csv`: one row per run;
- `results/cec2017_summary.csv`: grouped statistics per function and method.

Plot mean objective error:

```bash
pip install -e ".[plot]"
python scripts/plot_cec2017.py
```

## Smoke run

A numerically verified pilot subset is preferred before attempting the full matrix:

```bash
python scripts/run_cec2017.py \
  --functions 1,3,5,20 \
  --methods abc \
  --dimension 10 \
  --evaluations 5000
```
