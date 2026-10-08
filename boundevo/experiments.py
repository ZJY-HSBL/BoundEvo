"""Reproducible experiment helpers for BoundEvo."""

from __future__ import annotations

import csv
import statistics
import time
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .cec2017 import (
    PAPER_FUNCTION_IDS,
    CEC2017Case,
    make_cec2017_case,
    validate_function_ids,
)
from .coefficients import Method
from .optimizer import BoundEvo, BoundEvoConfig


@dataclass(frozen=True, slots=True)
class TrialRecord:
    function_id: int
    function_name: str
    dimension: int
    method: str
    repeat: int
    seed: int
    objective: float
    optimum: float
    error: float
    violation: float
    evaluations: int
    generations: int
    coefficient_attempts: int
    elapsed_seconds: float
    converged: bool


@dataclass(frozen=True, slots=True)
class HistoryRecord:
    function_id: int
    function_name: str
    dimension: int
    method: str
    repeat: int
    seed: int
    generation: int
    evaluations: int
    best_objective: float
    best_error: float
    best_violation: float
    worst_objective: float
    worst_violation: float


@dataclass(frozen=True, slots=True)
class SummaryRecord:
    function_id: int
    dimension: int
    method: str
    trials: int
    best_objective: float
    mean_objective: float
    median_objective: float
    mean_error: float
    median_error: float
    std_error: float
    mean_evaluations: float
    mean_elapsed_seconds: float
    mean_coefficient_attempts: float
    convergence_rate: float


def paper_config(
    *,
    method: Method = "abc",
    max_evaluations: int = 100_000,
    seed: int | None = None,
) -> BoundEvoConfig:
    """Return the main source-aligned configuration."""

    return BoundEvoConfig(
        population_size=100,
        parent_count=15,
        elite_parent_count=5,
        offspring_count=1,
        max_evaluations=max_evaluations,
        coefficient_method=method,
        seed=seed,
    )


def _config_for_run(
    config: BoundEvoConfig,
    *,
    method: Method,
    seed: int,
) -> BoundEvoConfig:
    return BoundEvoConfig(
        population_size=config.population_size,
        parent_count=config.parent_count,
        elite_parent_count=config.elite_parent_count,
        offspring_count=config.offspring_count,
        max_evaluations=config.max_evaluations,
        coefficient_method=method,
        seed=seed,
        convergence_atol=config.convergence_atol,
    )


def _append_history(
    target: list[HistoryRecord],
    *,
    case: CEC2017Case,
    method: Method,
    repeat: int,
    seed: int,
    states,
) -> None:
    for state in states:
        target.append(
            HistoryRecord(
                function_id=case.function_id,
                function_name=case.name,
                dimension=case.dimension,
                method=method,
                repeat=repeat,
                seed=seed,
                generation=state.generation,
                evaluations=state.evaluations,
                best_objective=state.best_objective,
                best_error=max(0.0, state.best_objective - case.optimum),
                best_violation=state.best_violation,
                worst_objective=state.worst_objective,
                worst_violation=state.worst_violation,
            )
        )


def run_case(
    case: CEC2017Case,
    *,
    method: Method,
    repeat: int,
    seed: int,
    config: BoundEvoConfig | None = None,
    history_records: list[HistoryRecord] | None = None,
    history_interval: int = 1,
) -> TrialRecord:
    base = config or paper_config(method=method, seed=seed)
    cfg = _config_for_run(base, method=method, seed=seed)

    start = time.perf_counter()
    result = BoundEvo(cfg).minimize(case.problem, history_interval=history_interval)
    elapsed = time.perf_counter() - start
    error = max(0.0, result.objective - case.optimum)
    if history_records is not None:
        _append_history(
            history_records,
            case=case,
            method=method,
            repeat=repeat,
            seed=seed,
            states=result.history,
        )
    return TrialRecord(
        function_id=case.function_id,
        function_name=case.name,
        dimension=case.dimension,
        method=method,
        repeat=repeat,
        seed=seed,
        objective=result.objective,
        optimum=case.optimum,
        error=error,
        violation=result.violation,
        evaluations=result.evaluations,
        generations=result.generations,
        coefficient_attempts=result.coefficient_attempts,
        elapsed_seconds=elapsed,
        converged=result.converged,
    )


def run_cec2017_suite(
    *,
    function_ids: Iterable[int] = PAPER_FUNCTION_IDS,
    dimension: int = 10,
    methods: Sequence[Method] = ("re", "edbf", "abc"),
    repeats: int = 1,
    base_seed: int = 42,
    max_evaluations: int = 100_000,
    history_records: list[HistoryRecord] | None = None,
    history_interval: int = 100,
) -> list[TrialRecord]:
    ids = validate_function_ids(function_ids)
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    if not methods:
        raise ValueError("at least one coefficient method is required")
    if history_interval < 1:
        raise ValueError("history_interval must be at least 1")

    records: list[TrialRecord] = []
    for fid in ids:
        case = make_cec2017_case(fid, dimension)
        for method_index, method in enumerate(methods):
            for repeat in range(repeats):
                seed = base_seed + fid * 10_000 + method_index * 1_000 + repeat
                records.append(
                    run_case(
                        case,
                        method=method,
                        repeat=repeat,
                        seed=seed,
                        config=paper_config(
                            method=method,
                            max_evaluations=max_evaluations,
                            seed=seed,
                        ),
                        history_records=history_records,
                        history_interval=history_interval,
                    )
                )
    return records


def summarize(records: Sequence[TrialRecord]) -> list[SummaryRecord]:
    groups: dict[tuple[int, int, str], list[TrialRecord]] = {}
    for record in records:
        groups.setdefault((record.function_id, record.dimension, record.method), []).append(record)

    summaries: list[SummaryRecord] = []
    for (function_id, dimension, method), items in sorted(groups.items()):
        objectives = [item.objective for item in items]
        errors = [item.error for item in items]
        evaluations = [float(item.evaluations) for item in items]
        elapsed = [item.elapsed_seconds for item in items]
        attempts = [float(item.coefficient_attempts) for item in items]
        convergence_rate = sum(item.converged for item in items) / len(items)
        summaries.append(
            SummaryRecord(
                function_id=function_id,
                dimension=dimension,
                method=method,
                trials=len(items),
                best_objective=min(objectives),
                mean_objective=statistics.fmean(objectives),
                median_objective=statistics.median(objectives),
                mean_error=statistics.fmean(errors),
                median_error=statistics.median(errors),
                std_error=statistics.stdev(errors) if len(errors) > 1 else 0.0,
                mean_evaluations=statistics.fmean(evaluations),
                mean_elapsed_seconds=statistics.fmean(elapsed),
                mean_coefficient_attempts=statistics.fmean(attempts),
                convergence_rate=convergence_rate,
            )
        )
    return summaries


def _write_dataclasses(path: str | Path, rows: Sequence[object]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("cannot write an empty result table")
    payload = [asdict(row) for row in rows]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(payload[0].keys()))
        writer.writeheader()
        writer.writerows(payload)


def write_trials_csv(path: str | Path, records: Sequence[TrialRecord]) -> None:
    _write_dataclasses(path, records)


def write_history_csv(path: str | Path, records: Sequence[HistoryRecord]) -> None:
    _write_dataclasses(path, records)


def write_summary_csv(path: str | Path, rows: Sequence[SummaryRecord]) -> None:
    _write_dataclasses(path, rows)
