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

## Run the 29-function matrix

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

Before launching the full matrix:

```bash
python scripts/run_cec2017.py \
  --functions 1,10,20,30 \
  --methods abc \
  --dimension 10 \
  --evaluations 5000
```
