# CEC2017 numerical reference backend

BoundEvo now supports two **independently implemented** CEC2017 backends.
The default remains `opfunu` for compatibility. For new scientific comparison
runs, select the reference-derived implementation explicitly.

## Why a second implementation?

During a real October 2026 pilot, `opfunu==1.0.1` returned F10 objective
values below its advertised global optimum (1000), and the F30 composition
objective was non-finite at a test point. An objective error clipped to zero
can conceal these integrity problems. See
[Issue #3](https://github.com/ZJY-HSBL/BoundEvo/issues/3).

The alternative is
[Duncan Tilley's `cec2017-py`](https://github.com/tilleyd/cec2017-py),
a NumPy implementation explicitly adapted from the original C code. It uses
official function indices F1..F30, including the deprecated F2 (excluded by
BoundEvo), and stores official rotation, shift, and shuffle data.

Reference source **pinned to commit**:

`424a9fa2757914c3e4cfdd8f59a268b1aeb3197f`

This is an independent reference-derived backend, **not** a statement that its
bytes are identical to the official benchmark C binary.

## Install

~~~bash
pip install -e ".[analysis,plot]"
pip install "git+https://github.com/tilleyd/cec2017-py.git@424a9fa2757914c3e4cfdd8f59a268b1aeb3197f"
~~~

## Python interface

~~~python
import numpy as np
from boundevo.cec2017 import make_cec2017_case

case = make_cec2017_case(30, 30, backend="reference")
print(case.optimum)  # 3000.0
print(case.problem.evaluate(np.zeros(30)).objective)
~~~

The reference backend supports 10, 30, 50 and 100 dimensions and **official**
CEC2017 identifiers F1, F3..F30. Passing F2 is deliberately rejected.

## CLI

~~~bash
boundevo benchmark \
  --backend reference \
  --config configs/cec2017.json \
  --dimension 30 \
  --repeats 10

boundevo sweep \
  --backend reference \
  --config configs/parent_sweep.json \
  --dimension 30

boundevo pipeline \
  --backend reference \
  --config configs/pipeline.json \
  --dimension 30
~~~

The resolved backend is written into each command's manifest so that data from
different implementations are not silently combined.

## Reproducible reference validation

The [reference-validation GitHub Actions workflow](../.github/workflows/reference-validation.yml)
performs a preflight on all **29 official functions** at D=10 and D=30.
Each is evaluated at the zero vector and five deterministic random points and
checked for nonfinite values and values below its known optimum.

It then evaluates F1, F3, F10 and F30 at D=30 with three coefficient
generators, ten matched initial seeds per problem, and 3,000 objective
evaluations per trial. Those **120 trials** are an extended pilot, not the full
29-function experiment with the publication-level evaluation budget.

The workflow stores raw trial CSV, grouped summaries, exact paired sign tests,
the numerical preflight table, a Markdown report and environment metadata.
On success the directory is committed under `docs/experiments/`, and
an Actions artifact is uploaded.

## Interpretation

- Benchmark implementations with different shifts, transforms, or composition
  arithmetic cannot be assumed numerically identical.
- A shared random seed makes the *initial population* identical across methods,
  but their subsequent random streams diverge.
- Exact sign-test p values are exploratory and unadjusted for multiplicity.
- 10 seeds and 4 functions do not establish superiority over a complete suite.
- To claim a faithful paper-level reproduction, match the original
  evaluation budget, test dimensions, stopping criteria and baseline algorithms,
  then validate all benchmark values against the organizers' reference.

The `opfunu` pilot is retained as historical evidence, not pooled with the
reference-derived experiments.
