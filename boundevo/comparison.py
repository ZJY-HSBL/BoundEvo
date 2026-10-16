"""Comparisons and Pareto analysis across completed experiment runs.

Scores are formed only from identical (CEC function, dimension, method) keys.
Mixed case coverage is rejected by default; partial comparisons must be
explicitly requested and display their restrictions.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from pathlib import Path

from .registry import read_benchmark_metrics, scan_runs


@dataclass(frozen=True, slots=True)
class RunScore:
    run_id: str
    matched_cases: int
    mean_error: float
    mean_runtime_seconds: float
    mean_evaluations: float
    pareto_efficient: bool


@dataclass(frozen=True, slots=True)
class Comparison:
    cases: tuple[tuple[int, int, str], ...]
    scores: tuple[RunScore, ...]
    warnings: tuple[str, ...]
    best_error_run: str
    fastest_run: str
    fewest_evaluations_run: str
    pareto_run_ids: tuple[str, ...]


def _dominates(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    """Pareto domination under minimization of all three measures."""

    return all(x <= y for x, y in zip(a, b, strict=True)) and any(
        x < y for x, y in zip(a, b, strict=True)
    )


def pareto_indices(points: list[tuple[float, ...]]) -> tuple[int, ...]:
    """Return indices of nondominated points, preserving input order."""

    if not points:
        return ()
    dimensions = len(points[0])
    if dimensions == 0:
        raise ValueError("Pareto points must have at least one dimension")
    if any(len(point) != dimensions for point in points):
        raise ValueError("all Pareto points must share the same dimensionality")
    if any(not math.isfinite(value) for point in points for value in point):
        raise ValueError("Pareto values must be finite")
    return tuple(
        i for i, point in enumerate(points)
        if not any(
            i != j and _dominates(challenger, point)
            for j, challenger in enumerate(points)
        )
    )


def compare_runs(
    root: str | Path = "results/runs",
    *,
    run_ids: tuple[str, ...] | None = None,
    allow_partial: bool = False,
) -> Comparison:
    """Score at least two completed runs on a strictly aligned cohort."""

    discovered = {entry.run_id: entry for entry in scan_runs(root)}
    if run_ids is None:
        chosen = [entry for entry in discovered.values() if entry.status == "complete"]
    else:
        if len(set(run_ids)) != len(run_ids):
            raise ValueError("duplicate run IDs are not allowed")
        unknown = set(run_ids) - set(discovered)
        if unknown:
            raise ValueError(f"unknown run IDs: {', '.join(sorted(unknown))}")
        chosen = [discovered[identifier] for identifier in run_ids]

    if len(chosen) < 2:
        raise ValueError("at least two completed runs are required for comparison")
    for entry in chosen:
        if entry.status != "complete":
            raise ValueError(f"run {entry.run_id!r} has status {entry.status!r}")

    metric_maps = [read_benchmark_metrics(entry) for entry in chosen]
    case_sets = [set(metrics) for metrics in metric_maps]
    aligned = set.intersection(*case_sets)
    if not aligned:
        raise ValueError("selected runs have no matching function/dimension/method cases")
    if not allow_partial and any(keys != aligned for keys in case_sets):
        raise ValueError(
            "benchmark case sets differ; rerun with --allow-partial to compare "
            "only their shared cases"
        )

    warnings: list[str] = []
    if any(keys != aligned for keys in case_sets):
        warnings.append(
            "Partial coverage: only shared benchmark cases are included; "
            "results cannot represent the excluded cases."
        )
    budgets = {entry.evaluation_budget for entry in chosen}
    if len(budgets) > 1:
        warnings.append(
            "Evaluation budgets differ: error and evaluation counts describe "
            "different stopping opportunities."
        )
    platforms = {entry.platform for entry in chosen}
    warnings.append(
        "Runtime measurements are not hardware-normalized; identical platform "
        "strings do not establish identical machines or system load."
    )
    if len(platforms) > 1 or None in platforms:
        warnings.append(
            "Runtime comparisons may additionally be confounded by different "
            "or unknown platforms."
        )
    seeds = {entry.base_seed for entry in chosen}
    if len(seeds) > 1:
        warnings.append(
            "Base seeds differ: stochastic outcomes may reflect different "
            "random initializations."
        )
    revisions = {entry.source_revision for entry in chosen}
    if len(revisions) > 1:
        warnings.append(
            "Source revisions differ: improvements cannot be attributed to one "
            "algorithmic change without further controlled experiments."
        )
    repeats = {entry.repeats for entry in chosen}
    if len(repeats) > 1:
        warnings.append("Repeat counts differ; mean estimates may have different uncertainty.")
    warnings.append(
        "Arithmetic mean error is scale-dependent across functions. "
        "Pareto membership is not proof of statistical superiority."
    )

    ordered_cases = tuple(sorted(aligned))
    raw_scores = []
    for entry, metrics in zip(chosen, metric_maps, strict=True):
        common = [metrics[key] for key in ordered_cases]
        raw_scores.append(
            (
                entry.run_id,
                statistics.fmean(metric.mean_error for metric in common),
                statistics.fmean(metric.mean_elapsed_seconds for metric in common),
                statistics.fmean(metric.mean_evaluations for metric in common),
            )
        )

    front = pareto_indices([row[1:] for row in raw_scores])
    scores = tuple(
        RunScore(
            run_id=row[0],
            matched_cases=len(ordered_cases),
            mean_error=row[1],
            mean_runtime_seconds=row[2],
            mean_evaluations=row[3],
            pareto_efficient=index in front,
        )
        for index, row in enumerate(raw_scores)
    )
    best_error = min(scores, key=lambda score: (score.mean_error, score.run_id))
    fastest = min(scores, key=lambda score: (score.mean_runtime_seconds, score.run_id))
    fewest = min(scores, key=lambda score: (score.mean_evaluations, score.run_id))
    return Comparison(
        cases=ordered_cases,
        scores=scores,
        warnings=tuple(warnings),
        best_error_run=best_error.run_id,
        fastest_run=fastest.run_id,
        fewest_evaluations_run=fewest.run_id,
        pareto_run_ids=tuple(scores[index].run_id for index in front),
    )


def render_comparison_markdown(comparison: Comparison) -> str:
    lines = [
        "# BoundEvo cross-run comparison",
        "",
        f"Aligned benchmark cases: **{len(comparison.cases)}**.",
        "",
        "| Run ID | Mean error ↓ | Mean runtime (s) ↓ | Mean evaluations ↓ | Pareto |",
        "|:---|---:|---:|---:|:---:|",
    ]
    for score in comparison.scores:
        lines.append(
            f"| {score.run_id} | {score.mean_error:.9g} | "
            f"{score.mean_runtime_seconds:.9g} | "
            f"{score.mean_evaluations:.9g} | "
            f"{'Yes' if score.pareto_efficient else 'No'} |"
        )

    lines.extend(
        [
            "",
            "## Criterion-specific leaders",
            "",
            f"- Lowest mean error: **{comparison.best_error_run}**",
            f"- Lowest mean runtime: **{comparison.fastest_run}**",
            f"- Fewest mean evaluations: **{comparison.fewest_evaluations_run}**",
            f"- Nondominated runs: **{', '.join(comparison.pareto_run_ids)}**",
            "",
            "There is no single automatically best overall run without a stated trade-off.",
            "",
            "## Matched cases",
            "",
            ", ".join(f"F{fid}/D{dim}/{method}" for fid, dim, method in comparison.cases),
            "",
            "## Comparability notes",
            "",
        ]
    )
    lines.extend(f"- {warning}" for warning in comparison.warnings)
    lines.append("")
    return "\n".join(lines)


def write_comparison_report(path: str | Path, comparison: Comparison) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_comparison_markdown(comparison), encoding="utf-8")
