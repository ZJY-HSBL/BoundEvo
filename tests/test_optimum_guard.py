"""Fail fast on benchmark objectives below their reported global optimum."""

import pytest

from boundevo.cec2017 import CEC2017Case
from boundevo.experiments import paper_config, run_case
from boundevo.problem import OptimizationProblem
from boundevo.sweep import run_parent_sweep_case


def _inconsistent_case() -> CEC2017Case:
    problem = OptimizationProblem(
        objective=lambda x: 0.0,
        lower=[-1.0] * 10,
        upper=[1.0] * 10,
    )
    return CEC2017Case(
        function_id=1,
        dimension=10,
        name="synthetic invalid global optimum",
        optimum=100.0,
        problem=problem,
    )


def test_main_case_rejects_impossibly_low_objective() -> None:
    with pytest.raises(RuntimeError, match="below its declared optimum"):
        run_case(
            _inconsistent_case(),
            method="abc",
            repeat=0,
            seed=1,
            config=paper_config(max_evaluations=100, seed=1),
        )


def test_parent_sweep_rejects_impossibly_low_objective() -> None:
    with pytest.raises(RuntimeError, match="below its declared optimum"):
        run_parent_sweep_case(
            _inconsistent_case(),
            parent_count=10,
            method="abc",
            repeat=0,
            seed=1,
            max_evaluations=100,
        )
