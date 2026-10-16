"""CEC 2017 benchmark integration.

The adapter is intentionally optional: BoundEvo itself depends only on NumPy.
Install the ``cec2017`` extra to run the full benchmark suite.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from importlib import import_module
from inspect import signature
from typing import Any

import numpy as np

from .problem import OptimizationProblem

# Official CEC2017 numbers use F1 and F3..F30 because F2 was excluded.
# O p f u n u's cec2017.py classes instead use sequential F1..F29:
# F2 in opfunu is the official F3 (Zakharov), and F29 is official F30.
PAPER_FUNCTION_IDS: tuple[int, ...] = (1, *range(3, 31))


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


def make_cec2017_case(function_id: int, dimension: int) -> CEC2017Case:
    """Create a CEC2017 case backed by opfunu."""

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
