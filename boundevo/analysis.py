"""Benchmark ranking and non-parametric statistical analysis."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MetricObservation:
    case: str
    method: str
    value: float


@dataclass(frozen=True, slots=True)
class RankResult:
    method: str
    mean_rank: float
    cases: int


@dataclass(frozen=True, slots=True)
class WinTieLoss:
    left: str
    right: str
    wins: int
    ties: int
    losses: int

    @property
    def cases(self) -> int:
        return self.wins + self.ties + self.losses


@dataclass(frozen=True, slots=True)
class WilcoxonResult:
    left: str
    right: str
    statistic: float
    pvalue: float
    adjusted_pvalue: float
    cases: int


@dataclass(frozen=True, slots=True)
class FriedmanResult:
    statistic: float
    pvalue: float
    cases: int
    methods: tuple[str, ...]


def load_summary_metric(
    path: str | Path,
    *,
    metric: str = "mean_error",
) -> list[MetricObservation]:
    """Load one numeric metric from a BoundEvo summary CSV."""

    input_path = Path(path)
    observations: list[MetricObservation] = []
    with input_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or ())
        required = {"function_id", "dimension", "method", metric}
        missing = required - fieldnames
        if missing:
            raise ValueError(f"summary CSV is missing fields: {sorted(missing)}")
        has_parent_count = "parent_count" in fieldnames
        for row in reader:
            case = f"F{int(row['function_id'])}/D{int(row['dimension'])}"
            if has_parent_count:
                case += f"/M{int(row['parent_count'])}"
            observations.append(
                MetricObservation(
                    case=case,
                    method=row["method"],
                    value=float(row[metric]),
                )
            )
    if not observations:
        raise ValueError("summary CSV contains no data rows")
    return observations


def _matrix(
    observations: Iterable[MetricObservation],
    methods: Iterable[str] | None = None,
) -> tuple[tuple[str, ...], dict[str, dict[str, float]]]:
    by_case: dict[str, dict[str, float]] = defaultdict(dict)
    discovered: set[str] = set()
    for item in observations:
        if item.method in by_case[item.case]:
            raise ValueError(f"duplicate method {item.method!r} for case {item.case!r}")
        by_case[item.case][item.method] = item.value
        discovered.add(item.method)

    selected = tuple(methods) if methods is not None else tuple(sorted(discovered))
    if len(set(selected)) != len(selected):
        raise ValueError("methods must be unique")
    if not selected:
        raise ValueError("at least one method is required")
    unknown = set(selected) - discovered
    if unknown:
        raise ValueError(f"methods not found in observations: {sorted(unknown)}")

    complete = {
        case: values
        for case, values in by_case.items()
        if all(method in values for method in selected)
    }
    if not complete:
        raise ValueError("no complete benchmark cases contain all selected methods")
    return selected, complete


def _average_case_ranks(
    values: dict[str, float],
    methods: tuple[str, ...],
    *,
    atol: float,
    rtol: float,
) -> dict[str, float]:
    ordered = sorted(methods, key=lambda method: values[method])
    ranks: dict[str, float] = {}
    index = 0
    while index < len(ordered):
        end = index + 1
        anchor = values[ordered[index]]
        while end < len(ordered) and math.isclose(
            values[ordered[end]],
            anchor,
            abs_tol=atol,
            rel_tol=rtol,
        ):
            end += 1
        average_rank = ((index + 1) + end) / 2.0
        for method in ordered[index:end]:
            ranks[method] = average_rank
        index = end
    return ranks


def rank_methods(
    observations: Iterable[MetricObservation],
    *,
    methods: Iterable[str] | None = None,
    atol: float = 1e-12,
    rtol: float = 1e-9,
) -> list[RankResult]:
    """Rank methods per case, then return mean ranks; lower is better."""

    selected, complete = _matrix(observations, methods)
    totals = {method: 0.0 for method in selected}
    for values in complete.values():
        ranks = _average_case_ranks(values, selected, atol=atol, rtol=rtol)
        for method in selected:
            totals[method] += ranks[method]
    cases = len(complete)
    return sorted(
        (
            RankResult(method=method, mean_rank=totals[method] / cases, cases=cases)
            for method in selected
        ),
        key=lambda row: (row.mean_rank, row.method),
    )


def win_tie_loss(
    observations: Iterable[MetricObservation],
    left: str,
    right: str,
    *,
    atol: float = 1e-12,
    rtol: float = 1e-9,
) -> WinTieLoss:
    """Compare two methods case by case for a lower-is-better metric."""

    _, complete = _matrix(observations, (left, right))
    wins = ties = losses = 0
    for values in complete.values():
        a, b = values[left], values[right]
        if math.isclose(a, b, abs_tol=atol, rel_tol=rtol):
            ties += 1
        elif a < b:
            wins += 1
        else:
            losses += 1
    return WinTieLoss(left, right, wins, ties, losses)


def _require_scipy():
    try:
        from scipy import stats
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            'statistical tests require the optional dependency: pip install -e ".[analysis]"'
        ) from exc
    return stats


def _paired_values(
    observations: Iterable[MetricObservation],
    left: str,
    right: str,
) -> tuple[list[float], list[float]]:
    _, complete = _matrix(observations, (left, right))
    ordered_cases = sorted(complete)
    return (
        [complete[case][left] for case in ordered_cases],
        [complete[case][right] for case in ordered_cases],
    )


def _holm_adjust(pvalues: list[float]) -> list[float]:
    count = len(pvalues)
    if count == 0:
        return []
    order = sorted(range(count), key=pvalues.__getitem__)
    adjusted = [1.0] * count
    running = 0.0
    for rank, index in enumerate(order):
        candidate = min(1.0, (count - rank) * pvalues[index])
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted


def wilcoxon_against_reference(
    observations: Iterable[MetricObservation],
    *,
    reference: str,
    methods: Iterable[str] | None = None,
    atol: float = 1e-12,
    rtol: float = 1e-9,
) -> list[WilcoxonResult]:
    """Run paired Wilcoxon tests versus reference with Holm correction."""

    stats = _require_scipy()
    observations = list(observations)
    selected, _ = _matrix(observations, methods)
    if reference not in selected:
        raise ValueError(f"reference method {reference!r} is not selected")

    raw: list[tuple[str, float, float, int]] = []
    for method in selected:
        if method == reference:
            continue
        left, right = _paired_values(observations, reference, method)
        if all(
            math.isclose(a, b, abs_tol=atol, rel_tol=rtol)
            for a, b in zip(left, right, strict=True)
        ):
            statistic, pvalue = 0.0, 1.0
        else:
            result = stats.wilcoxon(left, right, alternative="two-sided", method="auto")
            statistic, pvalue = float(result.statistic), float(result.pvalue)
        raw.append((method, statistic, pvalue, len(left)))

    adjusted = _holm_adjust([item[2] for item in raw])
    return [
        WilcoxonResult(
            left=reference,
            right=method,
            statistic=statistic,
            pvalue=pvalue,
            adjusted_pvalue=adjusted_pvalue,
            cases=cases,
        )
        for (method, statistic, pvalue, cases), adjusted_pvalue in zip(
            raw,
            adjusted,
            strict=True,
        )
    ]


def friedman_test(
    observations: Iterable[MetricObservation],
    *,
    methods: Iterable[str] | None = None,
) -> FriedmanResult:
    """Run the Friedman test across at least three methods."""

    stats = _require_scipy()
    selected, complete = _matrix(observations, methods)
    if len(selected) < 3:
        raise ValueError("Friedman test requires at least three methods")
    ordered_cases = sorted(complete)
    samples = [
        [complete[case][method] for case in ordered_cases]
        for method in selected
    ]
    result = stats.friedmanchisquare(*samples)
    return FriedmanResult(
        statistic=float(result.statistic),
        pvalue=float(result.pvalue),
        cases=len(ordered_cases),
        methods=selected,
    )


def render_analysis_report(
    observations: Iterable[MetricObservation],
    *,
    metric: str,
    reference: str = "abc",
    methods: Iterable[str] | None = None,
) -> str:
    """Render ranks, W/T/L, Wilcoxon, and Friedman results as Markdown."""

    observations = list(observations)
    selected, complete = _matrix(observations, methods)
    ranks = rank_methods(observations, methods=selected)
    if reference not in selected:
        raise ValueError(f"reference method {reference!r} is not selected")

    lines = [
        "# BoundEvo benchmark analysis",
        "",
        f"- Metric: {metric} (lower is better)",
        f"- Complete benchmark cases: {len(complete)}",
        f"- Methods: {', '.join(selected)}",
        f"- Reference method: {reference}",
        "",
        "## Mean ranks",
        "",
        "| Rank | Method | Mean rank | Cases |",
        "|---:|:---|---:|---:|",
    ]
    for index, row in enumerate(ranks, start=1):
        lines.append(f"| {index} | {row.method} | {row.mean_rank:.6g} | {row.cases} |")

    lines.extend(
        [
            "",
            "## Win / Tie / Loss",
            "",
            f"Comparisons are reported from the perspective of {reference}.",
            "",
            "| Comparison | Win | Tie | Loss | Cases |",
            "|:---|---:|---:|---:|---:|",
        ]
    )
    for method in selected:
        if method == reference:
            continue
        row = win_tie_loss(observations, reference, method)
        lines.append(
            f"| {reference} vs {method} | {row.wins} | {row.ties} | "
            f"{row.losses} | {row.cases} |"
        )

    wilcoxon = wilcoxon_against_reference(
        observations,
        reference=reference,
        methods=selected,
    )
    lines.extend(
        [
            "",
            "## Wilcoxon signed-rank tests",
            "",
            (
                "Two-sided paired tests; Holm-adjusted p-values correct the "
                "reference-versus-others family."
            ),
            "",
            "| Comparison | Statistic | p | Holm p | Cases |",
            "|:---|---:|---:|---:|---:|",
        ]
    )
    for row in wilcoxon:
        lines.append(
            f"| {row.left} vs {row.right} | {row.statistic:.6g} | "
            f"{row.pvalue:.6g} | {row.adjusted_pvalue:.6g} | {row.cases} |"
        )

    friedman = friedman_test(observations, methods=selected)
    lines.extend(
        [
            "",
            "## Friedman test",
            "",
            f"- Statistic: {friedman.statistic:.6g}",
            f"- p-value: {friedman.pvalue:.6g}",
            f"- Cases: {friedman.cases}",
            f"- Methods: {', '.join(friedman.methods)}",
            "",
            (
                "Statistical significance does not by itself establish practical superiority; "
                "interpret these tests together with error magnitude, runtime, and "
                "function-evaluation counts."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_analysis_report(path: str | Path, report: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
