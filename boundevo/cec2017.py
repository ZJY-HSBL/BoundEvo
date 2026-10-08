"""CEC 2017 benchmark integration.

The adapter is intentionally optional: BoundEvo itself depends only on NumPy.
Install the ``cec2017`` extra to run the full benchmark suite.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from importlib import import_module
from typing import Any

import numpy as np

from .problem import OptimizationProblem

# The source experiment reports 29 CEC2017 problems and its result table contains
# F1 and F3..F30, i.e. F2 is excluded.
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
    invalid = [fid for fid in ids if fid < 1 or fid > 30]
    if invalid:
        raise ValueError(f"CEC2017 function ids must be in [1, 30], got {invalid}")
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
    if not 1 <= function_id <= 30:
        raise ValueError("function_id must be in [1, 30]")
    return f"F{function_id}2017"


def make_cec2017_case(function_id: int, dimension: int) -> CEC2017Case:
    """Create a CEC2017 case backed by opfunu."""

    if dimension < 2:
        raise ValueError("CEC2017 dimension must be at least 2")
    module = _load_cec2017_module()
    class_name = _benchmark_class_name(function_id)
    benchmark_class = getattr(module, class_name, None)
    if benchmark_class is None:
        raise RuntimeError(f"opfunu does not expose {class_name}")

    benchmark = benchmark_class(ndim=dimension)
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
    name = str(getattr(benchmark, "name", class_name))
    return CEC2017Case(function_id, dimension, name, optimum, problem)
