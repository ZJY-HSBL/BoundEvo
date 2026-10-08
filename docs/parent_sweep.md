# Parent-count sweep reproduction

This stage reproduces the experiment structure used to study the effect of the
multi-parent recombination scale `M`.

## Source-aligned matrix

The source material explicitly varies:

- `M = 10, 11, 12, 13, 14, 15, 16`;
- CEC2017 functions `F1`, `F10`, `F20`, and `F30`;
- three coefficient-generation variants corresponding to the RE-based EP-GTA,
  the EDBF-based variant, and the adaptive-boundary variant;
- three reported comparison indicators: best solution, program runtime, and
  number of function evaluations.

The fixed main settings remain `N=100`, `K=5`, and `L=1`.

The benchmark dimensionality is not stated in the extracted experiment-setting
paragraph, so the CLI keeps it explicit. The default `--dimension 10` is a
convenience value, not a claim about the source experiment.

## Run

Install the benchmark dependency:

```bash
pip install -e ".[cec2017]"
```

Smoke test:

```bash
python scripts/run_parent_sweep.py \
  --functions 1 \
  --parents 10-11 \
  --methods abc \
  --dimension 10 \
  --evaluations 500
```

Full source-aligned matrix:

```bash
python scripts/run_parent_sweep.py \
  --functions paper \
  --parents 10-16 \
  --methods re edbf abc \
  --dimension 10 \
  --repeats 1 \
  --evaluations 100000
```

For stochastic reporting, increase `--repeats`; the generated Markdown tables
then retain the best objective but report mean runtime and mean evaluation count.

Outputs:

- `results/parent_sweep_trials.csv`;
- `results/parent_sweep_summary.csv`;
- `results/parent_sweep_tables.md`.

## Plot

```bash
pip install -e ".[plot]"
python scripts/plot_parent_sweep.py
```

This produces separate error, runtime, and function-evaluation figures for each
of F1, F10, F20, and F30.

## Coefficient-generation efficiency experiment

The source also studies coefficient-vector generation efficiency for
`M = 1..20`, using one million experiments for the RE curve and comparing it
with EDBF and the adaptive-boundary method. BoundEvo reproduces that experiment
with vectorized Monte Carlo batches:

```bash
python scripts/reproduce_efficiency_figure.py --trials 1000000
python scripts/plot_efficiency_figure.py
```

Efficiency is defined as the fraction of proposed coefficient vectors whose
derived final coefficient lies inside `[-0.5, 1.5]`. The adaptive-boundary
method has exact efficiency 1 by construction.
