"""CEC 2017 benchmark integration.

The adapter is intentionally optional: BoundEvo itself depends only on NumPy.
Install the ``cec2017`` extra to run the full benchmark suite.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from importlib import import_module
from inspect import signature
from typing import Any, Literal

import numpy as np

from .problem import OptimizationProblem

# Official CEC2017 numbers use F1 and F3..F30 because F2 was excluded.
# O p f u n u's cec2017.py classes instead use sequential F1..F29:
# F2 in opfunu is the official F3 (Zakharov), and F29 is official F30.
PAPER_FUNCTION_IDS: tuple[int, ...] = (1, *range(3, 31))
Backend = Literal["opfunu", "reference"]
REFERENCE_REPO = "https://github.com/tilleyd/cec2017-py"
REFERENCE_COMMIT = "424a9fa2757914c3e4cfdd8f59a268b1aeb3197f"



@dataclass(frozen=True, slots=True)
class CEC2017Case:
    """A BoundEvo problem plus CEC metadata."""

    function_id: int
    dimension: int
    name: str
    optimum: float
    problem: OptimizationProblem


def validate_function_ids(function_ids: Iterable[int]) -> tuple[int, ...]:
    ids = tuple(int(fid) for fid in function_ids)
    if not ids:
        raise ValueError("at least one CEC2017 function id is required")
    invalid = [fid for fid in ids if fid not in PAPER_FUNCTION_IDS]
    if invalid:
        raise ValueError(
            f"CEC2017 official function ids must be F1 or F3..F30; got {invalid}"
        )
    return ids


def _load_cec2017_module() -> Any:
    try:
        return import_module("opfunu.cec_based.cec2017")
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("opfunu"):
            raise RuntimeError(
                'CEC2017 support requires the optional dependency: pip install -e ".[cec2017]"'
            ) from exc
        raise


def _benchmark_class_name(function_id: int) -> str:
    if function_id not in PAPER_FUNCTION_IDS:
        raise ValueError("official CEC2017 function id must be 1 or 3..30")
    # opfunu skips the withdrawn F2 and renumbers the remaining benchmarks.
    opfunu_id = function_id if function_id == 1 else function_id - 1
    return f"F{opfunu_id}2017"


def make_cec2017_case(
    function_id: int,
    dimension: int,
    *,
    backend: Backend = "opfunu",
) -> CEC2017Case:
    """Create a benchmark using opfunu or the independent C-derived Python suite."""

    validate_function_ids((function_id,))
    if backend == "reference":
        return _make_reference_case(function_id, dimension)
    if backend != "opfunu":
        raise ValueError("backend must be 'reference' or 'opfunu'")
    if dimension < 2:
        raise ValueError("CEC2017 dimension must be at least 2")
    module = _load_cec2017_module()
    class_name = _benchmark_class_name(function_id)
    benchmark_class = getattr(module, class_name, None)
    if benchmark_class is None:
        raise RuntimeError(f"opfunu does not expose {class_name}")

    # The upstream class defaults use the *renumbered* bias and, for some
    # functions, renumbered shift/rotation file names. Explicitly supply
    # the official CEC2017 index to restore the published F_i convention.
    params = signature(benchmark_class).parameters
    kwargs: dict[str, Any] = {
        "ndim": dimension,
        "f_bias": float(function_id * 100),
    }
    data_options = {
        "f_shift": f"shift_data_{function_id}",
        "f_matrix": f"M_{function_id}_D",
        "f_shuffle": f"shuffle_data_{function_id}_D",
    }
    for key, value in data_options.items():
        if key in params:
            kwargs[key] = value
    benchmark = benchmark_class(**kwargs)
    lower = np.asarray(benchmark.lb, dtype=np.float64)
    upper = np.asarray(benchmark.ub, dtype=np.float64)
    if lower.shape != (dimension,) or upper.shape != (dimension,):
        raise RuntimeError(
            f"{class_name} returned bounds with shapes {lower.shape} and {upper.shape}, "
            f"expected {(dimension,)}"
        )

    problem = OptimizationProblem(
        objective=lambda x, fn=benchmark.evaluate: float(fn(x)),
        lower=lower,
        upper=upper,
    )
    optimum = float(benchmark.f_global)
    upstream_name = str(getattr(benchmark, "name", class_name))
    description = upstream_name.split(": ", maxsplit=1)[-1]
    name = f"F{function_id}: {description}"
    return CEC2017Case(function_id, dimension, name, optimum, problem)


def _make_reference_case(function_id: int, dimension: int) -> CEC2017Case:
    """Use Duncan Tilley's CEC2017 implementation adapted from the original C.

    Unlike the opfunu classes, this implementation preserves official F1..F30
    IDs and embeds the original shift/rotation/shuffle benchmark data. It is
    still an independently maintained reference-derived implementation.
    """

    if dimension not in (10, 30, 50, 100):
        raise ValueError(
            "reference backend requires one of dimensions 10, 30, 50, 100"
        )
    try:
        functions = import_module("cec2017.functions")
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("cec2017"):
            raise RuntimeError(
                "reference CEC2017 backend not installed; use "
                f"pip install git+{REFERENCE_REPO}.git@{REFERENCE_COMMIT}"
            ) from exc
        raise
    objective = getattr(functions, f"f{function_id}", None)
    if objective is None:
        raise RuntimeError(f"reference CEC2017 backend lacks f{function_id}")

    def evaluate(point: np.ndarray) -> float:
        result = np.asarray(
            objective(np.asarray(point, dtype=np.float64)[None, :]),
            dtype=np.float64,
        )
        if result.shape != (1,):
            raise RuntimeError(
                f"reference f{function_id} returned shape {result.shape}, expected (1,)"
            )
        return float(result[0])

    bounds = np.full(dimension, 100.0, dtype=np.float64)
    return CEC2017Case(
        function_id=function_id,
        dimension=dimension,
        name=f"F{function_id}: CEC2017 reference-derived implementation",
        optimum=float(function_id * 100),
        problem=OptimizationProblem(evaluate, lower=-bounds, upper=bounds),
    )
