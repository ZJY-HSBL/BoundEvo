"""Source-aligned parent-count sweep helpers.

The source experiment varies the multi-parent recombination size M from 10 to 16
on CEC2017 functions F1, F10, F20, and F30 while keeping the population size,
elite-parent count, and offspring count fixed.
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .cec2017 import CEC2017Case, make_cec2017_case, validate_function_ids
from .coefficients import Method
from .experiments import _write_dataclasses
from .optimizer import BoundEvo, BoundEvoConfig

PAPER_SWEEP_FUNCTION_IDS: tuple[int, ...] = (1, 10, 20, 30)
PAPER_PARENT_COUNTS: tuple[int, ...] = tuple(range(10, 17))
METHOD_LABELS: dict[str, str] = {
    "re": "EP-GTA (RE)",
    "edbf": "EDBF-GTA",
    "abc": "BoundEvo (ABC)",
}


@dataclass(frozen=True, slots=True)
class ParentSweepTrial:
    function_id: int
    function_name: str
    dimension: int
    parent_count: int
    method: str
    repeat: int
    seed: int
    objective: float
    optimum: float
    error: float
    evaluations: int
    generations: int
    coefficient_attempts: int
    elapsed_seconds: float
    converged: bool


@dataclass(frozen=True, slots=True)
class ParentSweepSummary:
    function_id: int
    dimension: int
    parent_count: int
    method: str
    trials: int
    best_objective: float
    best_error: float
    mean_objective: float
    mean_error: float
    std_error: float
    mean_evaluations: float
    mean_elapsed_seconds: float
    mean_coefficient_attempts: float
    convergence_rate: float


def sweep_config(
    parent_count: int,
    *,
    method: Method = "abc",
    max_evaluations: int = 100_000,
    seed: int | None = None,
) -> BoundEvoConfig:
    """Build the source-aligned configuration for a selected M value."""

    if parent_count < 5:
        raise ValueError("parent_count must be at least the fixed elite-parent count K=5")
    if parent_count > 100:
        raise ValueError("parent_count cannot exceed the fixed population size N=100")
    return BoundEvoConfig(
        population_size=100,
        parent_count=parent_count,
        elite_parent_count=5,
        offspring_count=1,
        max_evaluations=max_evaluations,
        coefficient_method=method,
        seed=seed,
    )


def run_parent_sweep_case(
    case: CEC2017Case,
    *,
    parent_count: int,
    method: Method,
    repeat: int,
    seed: int,
    max_evaluations: int = 100_000,
) -> ParentSweepTrial:
    cfg = sweep_config(
        parent_count,
        method=method,
        max_evaluations=max_evaluations,
        seed=seed,
    )
    start = time.perf_counter()
    result = BoundEvo(cfg).minimize(case.problem)
    elapsed = time.perf_counter() - start
    error = max(0.0, result.objective - case.optimum)
    return ParentSweepTrial(
        function_id=case.function_id,
        function_name=case.name,
        dimension=case.dimension,
        parent_count=parent_count,
        method=method,
        repeat=repeat,
        seed=seed,
        objective=result.objective,
        optimum=case.optimum,
        error=error,
        evaluations=result.evaluations,
        generations=result.generations,
        coefficient_attempts=result.coefficient_attempts,
        elapsed_seconds=elapsed,
        converged=result.converged,
    )


def run_parent_count_sweep(
    *,
    function_ids: Iterable[int] = PAPER_SWEEP_FUNCTION_IDS,
    parent_counts: Iterable[int] = PAPER_PARENT_COUNTS,
    dimension: int = 10,
    methods: Sequence[Method] = ("re", "edbf", "abc"),
    repeats: int = 1,
    base_seed: int = 42,
    max_evaluations: int = 100_000,
) -> list[ParentSweepTrial]:
    ids = validate_function_ids(function_ids)
    counts = tuple(int(value) for value in parent_counts)
    if not counts:
        raise ValueError("at least one parent count is required")
    for count in counts:
        sweep_config(count, max_evaluations=max_evaluations)
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    if not methods:
        raise ValueError("at least one coefficient method is required")

    records: list[ParentSweepTrial] = []
    for fid in ids:
        case = make_cec2017_case(fid, dimension)
        for parent_count in counts:
            for method_index, method in enumerate(methods):
                for repeat in range(repeats):
                    seed = (
                        base_seed
                        + fid * 100_000
                        + parent_count * 1_000
                        + method_index * 100
                        + repeat
                    )
                    records.append(
                        run_parent_sweep_case(
                            case,
                            parent_count=parent_count,
                            method=method,
                            repeat=repeat,
                            seed=seed,
                            max_evaluations=max_evaluations,
                        )
                    )
    return records


def summarize_parent_sweep(
    records: Sequence[ParentSweepTrial],
) -> list[ParentSweepSummary]:
    groups: dict[tuple[int, int, int, str], list[ParentSweepTrial]] = {}
    for record in records:
        key = (
            record.function_id,
            record.dimension,
            record.parent_count,
            record.method,
        )
        groups.setdefault(key, []).append(record)

    rows: list[ParentSweepSummary] = []
    for (function_id, dimension, parent_count, method), items in sorted(groups.items()):
        objectives = [item.objective for item in items]
        errors = [item.error for item in items]
        evaluations = [float(item.evaluations) for item in items]
        elapsed = [item.elapsed_seconds for item in items]
        attempts = [float(item.coefficient_attempts) for item in items]
        rows.append(
            ParentSweepSummary(
                function_id=function_id,
                dimension=dimension,
                parent_count=parent_count,
                method=method,
                trials=len(items),
                best_objective=min(objectives),
                best_error=min(errors),
                mean_objective=statistics.fmean(objectives),
                mean_error=statistics.fmean(errors),
                std_error=statistics.stdev(errors) if len(errors) > 1 else 0.0,
                mean_evaluations=statistics.fmean(evaluations),
                mean_elapsed_seconds=statistics.fmean(elapsed),
                mean_coefficient_attempts=statistics.fmean(attempts),
                convergence_rate=sum(item.converged for item in items) / len(items),
            )
        )
    return rows


def write_parent_sweep_trials_csv(
    path: str | Path,
    rows: Sequence[ParentSweepTrial],
) -> None:
    _write_dataclasses(path, rows)


def write_parent_sweep_summary_csv(
    path: str | Path,
    rows: Sequence[ParentSweepSummary],
) -> None:
    _write_dataclasses(path, rows)


def _fmt(value: float) -> str:
    return f"{value:.10g}"


def render_source_style_tables(rows: Sequence[ParentSweepSummary]) -> str:
    """Render one Markdown table per benchmark using the source's three metrics."""

    grouped: dict[int, list[ParentSweepSummary]] = {}
    for row in rows:
        grouped.setdefault(row.function_id, []).append(row)

    sections = [
        "# Parent-count sweep tables",
        "",
        (
            "Metrics follow the source comparison: best objective, elapsed time, and "
            "function evaluations. With repeated trials, elapsed time and evaluations "
            "are reported as means."
        ),
        "",
    ]
    for function_id in sorted(grouped):
        sections.extend(
            [
                f"## F{function_id}",
                "",
                "| M | Method | Best objective | Mean runtime (s) | Mean evaluations |",
                "|---:|:---|---:|---:|---:|",
            ]
        )
        for row in sorted(
            grouped[function_id],
            key=lambda item: (item.parent_count, item.method),
        ):
            label = METHOD_LABELS.get(row.method, row.method)
            sections.append(
                "| "
                f"{row.parent_count} | {label} | {_fmt(row.best_objective)} | "
                f"{_fmt(row.mean_elapsed_seconds)} | {_fmt(row.mean_evaluations)} |"
            )
        sections.append("")
    return "\n".join(sections)


def write_source_style_tables(
    path: str | Path,
    rows: Sequence[ParentSweepSummary],
) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_source_style_tables(rows), encoding="utf-8")
