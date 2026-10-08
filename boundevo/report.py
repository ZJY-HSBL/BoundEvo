"""Standalone HTML reporting for BoundEvo experiment artifacts."""

from __future__ import annotations

import csv
import html
import json
import math
import statistics
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .analysis import load_summary_metric, rank_methods, win_tie_loss

_PALETTE = ("#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _fmt(value: float) -> str:
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude >= 1e5 or magnitude < 1e-4:
        return f"{value:.4e}"
    return f"{value:.6g}"


def _table(headers: list[str], rows: Iterable[Iterable[object]]) -> str:
    header_html = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(value))}</td>" for value in row)
        body.append(f"<tr>{cells}</tr>")
    return (
        '<div class="table-wrap"><table><thead><tr>'
        + header_html
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def _rank_section(path: Path, title: str) -> str:
    observations = load_summary_metric(path, metric="mean_error")
    methods = tuple(sorted({item.method for item in observations}))
    ranks = rank_methods(observations, methods=methods)
    pieces = [
        f"<section><h2>{html.escape(title)}</h2>",
        "<p>Average ranks use <code>mean_error</code>; lower is better.</p>",
        _table(
            ["Rank", "Method", "Mean rank", "Cases"],
            [
                (index, row.method, _fmt(row.mean_rank), row.cases)
                for index, row in enumerate(ranks, start=1)
            ],
        ),
    ]
    if "abc" in methods and len(methods) > 1:
        comparisons = []
        for method in methods:
            if method == "abc":
                continue
            row = win_tie_loss(observations, "abc", method)
            comparisons.append(
                (
                    f"abc vs {method}",
                    row.wins,
                    row.ties,
                    row.losses,
                    row.cases,
                )
            )
        pieces.extend(
            [
                "<h3>Win / Tie / Loss</h3>",
                _table(["Comparison", "Win", "Tie", "Loss", "Cases"], comparisons),
            ]
        )
    pieces.append("</section>")
    return "".join(pieces)


def _runtime_section(path: Path, title: str) -> str:
    rows = _read_csv(path)
    by_method: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_method[row["method"]].append(row)

    table_rows = []
    for method, items in sorted(by_method.items()):
        runtimes = [float(item["mean_elapsed_seconds"]) for item in items]
        evaluations = [float(item["mean_evaluations"]) for item in items]
        table_rows.append(
            (
                method,
                len(items),
                _fmt(statistics.fmean(runtimes)),
                _fmt(statistics.fmean(evaluations)),
            )
        )
    return "".join(
        [
            f"<section><h2>{html.escape(title)}</h2>",
            "<p>Aggregate operational metrics across the rows in this summary.</p>",
            _table(
                ["Method", "Rows", "Mean runtime (s)", "Mean evaluations"],
                table_rows,
            ),
            "</section>",
        ]
    )


def _downsample(points: list[tuple[float, float]], max_points: int = 240) -> list[tuple[float, float]]:
    if len(points) <= max_points:
        return points
    if max_points < 2:
        return [points[-1]]
    step = (len(points) - 1) / (max_points - 1)
    indices = sorted({round(index * step) for index in range(max_points)})
    return [points[index] for index in indices]


def _svg_line_chart(
    series: dict[str, list[tuple[float, float]]],
    *,
    x_label: str,
    y_label: str,
    log_y: bool = False,
) -> str:
    cleaned = {
        label: _downsample(sorted(points))
        for label, points in series.items()
        if points
    }
    if not cleaned:
        return "<p class=\"muted\">No chart data available.</p>"

    all_points = [point for points in cleaned.values() for point in points]
    x_values = [point[0] for point in all_points]
    raw_y_values = [point[1] for point in all_points]

    def transform_y(value: float) -> float:
        if log_y:
            return math.log10(max(value, 1e-16))
        return value

    y_values = [transform_y(value) for value in raw_y_values]
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    if math.isclose(x_min, x_max):
        x_max = x_min + 1.0
    if math.isclose(y_min, y_max):
        y_max = y_min + 1.0

    width, height = 760, 330
    left, right, top, bottom = 72, 22, 24, 58
    plot_width = width - left - right
    plot_height = height - top - bottom

    def sx(value: float) -> float:
        return left + (value - x_min) / (x_max - x_min) * plot_width

    def sy(value: float) -> float:
        transformed = transform_y(value)
        return top + (y_max - transformed) / (y_max - y_min) * plot_height

    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img">',
        (
            f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" '
            f'y2="{top + plot_height}" class="axis"/>'
        ),
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" class="axis"/>',
    ]

    for index in range(5):
        fraction = index / 4
        x = left + fraction * plot_width
        y = top + fraction * plot_height
        x_value = x_min + fraction * (x_max - x_min)
        y_transformed = y_max - fraction * (y_max - y_min)
        y_value = 10**y_transformed if log_y else y_transformed
        parts.extend(
            [
                (
                    f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" '
                    f'y2="{y:.2f}" class="grid"/>'
                ),
                (
                    f'<text x="{x:.2f}" y="{top + plot_height + 22}" '
                    f'class="tick" text-anchor="middle">{html.escape(_fmt(x_value))}</text>'
                ),
                (
                    f'<text x="{left - 10}" y="{y + 4:.2f}" class="tick" '
                    f'text-anchor="end">{html.escape(_fmt(y_value))}</text>'
                ),
            ]
        )

    legend_x = left + 8
    legend_y = top + 12
    for index, (label, points) in enumerate(sorted(cleaned.items())):
        color = _PALETTE[index % len(_PALETTE)]
        coords = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in points)
        parts.append(
            f'<polyline points="{coords}" fill="none" stroke="{color}" '
            'stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>'
        )
        ly = legend_y + index * 20
        parts.extend(
            [
                (
                    f'<line x1="{legend_x}" y1="{ly}" x2="{legend_x + 22}" y2="{ly}" '
                    f'stroke="{color}" stroke-width="3"/>'
                ),
                (
                    f'<text x="{legend_x + 28}" y="{ly + 4}" class="legend">'
                    f"{html.escape(label)}</text>"
                ),
            ]
        )

    parts.extend(
        [
            (
                f'<text x="{left + plot_width / 2:.2f}" y="{height - 12}" '
                f'class="axis-label" text-anchor="middle">{html.escape(x_label)}</text>'
            ),
            (
                f'<text x="18" y="{top + plot_height / 2:.2f}" class="axis-label" '
                f'text-anchor="middle" '
                f'transform="rotate(-90 18 {top + plot_height / 2:.2f})">'
                f"{html.escape(y_label)}</text>"
            ),
            "</svg>",
        ]
    )
    return "".join(parts)


def _convergence_section(path: Path) -> str:
    rows = _read_csv(path)
    grouped: dict[int, dict[str, dict[int, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for row in rows:
        grouped[int(row["function_id"])][row["method"]][int(row["evaluations"])].append(
            float(row["best_error"])
        )

    charts = []
    for function_id in sorted(grouped):
        series: dict[str, list[tuple[float, float]]] = {}
        for method, by_eval in grouped[function_id].items():
            series[method] = [
                (float(evaluation), statistics.fmean(values))
                for evaluation, values in sorted(by_eval.items())
            ]
        charts.append(
            "".join(
                [
                    '<article class="chart-card">',
                    f"<h3>F{function_id}</h3>",
                    _svg_line_chart(
                        series,
                        x_label="Function evaluations",
                        y_label="Mean best error",
                        log_y=True,
                    ),
                    "</article>",
                ]
            )
        )
    return (
        "<section><h2>Convergence history</h2>"
        "<p>Mean sampled best-error trajectories across repeated trials.</p>"
        '<div class="chart-grid">'
        + "".join(charts)
        + "</div></section>"
    )


def _sensitivity_section(path: Path) -> str:
    rows = _read_csv(path)
    grouped: dict[int, dict[str, list[tuple[float, float]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        grouped[int(row["function_id"])][row["method"]].append(
            (float(row["parent_count"]), float(row["mean_error"]))
        )

    charts = []
    for function_id in sorted(grouped):
        charts.append(
            "".join(
                [
                    '<article class="chart-card">',
                    f"<h3>F{function_id}</h3>",
                    _svg_line_chart(
                        dict(grouped[function_id]),
                        x_label="Parent count M",
                        y_label="Mean error",
                        log_y=True,
                    ),
                    "</article>",
                ]
            )
        )
    return (
        "<section><h2>Parent-count sensitivity</h2>"
        "<p>Objective error versus multi-parent recombination scale M.</p>"
        '<div class="chart-grid">'
        + "".join(charts)
        + "</div></section>"
    )


def _efficiency_section(path: Path) -> str:
    rows = _read_csv(path)
    by_method: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for row in rows:
        by_method[row["method"]].append(
            (int(row["parent_count"]), float(row["efficiency"]))
        )
    table_rows = []
    for method, points in sorted(by_method.items()):
        points.sort()
        mean_efficiency = statistics.fmean(point[1] for point in points)
        last_m, last_efficiency = points[-1]
        table_rows.append(
            (
                method,
                len(points),
                _fmt(mean_efficiency),
                last_m,
                _fmt(last_efficiency),
            )
        )
    chart_series = {
        method: [(float(parent_count), efficiency) for parent_count, efficiency in points]
        for method, points in by_method.items()
    }
    return "".join(
        [
            "<section><h2>Coefficient-generation efficiency</h2>",
            "<p>Summary and curve for the M-versus-efficiency experiment.</p>",
            _svg_line_chart(
                chart_series,
                x_label="Parent count M",
                y_label="Generation efficiency",
            ),
            _table(
                [
                    "Method",
                    "M points",
                    "Mean efficiency",
                    "Largest M",
                    "Efficiency at largest M",
                ],
                table_rows,
            ),
            "</section>",
        ]
    )


def _manifest_section(paths: list[Path]) -> str:
    cards = []
    for path in paths:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            payload: dict[str, Any] = json.load(handle)
        command = html.escape(str(payload.get("command", path.stem)))
        created = html.escape(str(payload.get("created_at_utc", "")))
        version_value = html.escape(str(payload.get("boundevo_version", "")))
        revision = html.escape(str(payload.get("source_revision", "")))
        run_id = html.escape(str(payload.get("run_id", "")))
        config = html.escape(
            json.dumps(payload.get("config", {}), indent=2, ensure_ascii=False)
        )
        run_line = f"<br><strong>Run ID:</strong> <code>{run_id}</code>" if run_id else ""
        cards.append(
            "".join(
                [
                    '<article class="manifest">',
                    f"<h3>{command}</h3>",
                    f"<p><strong>Created:</strong> {created}<br>",
                    f"<strong>BoundEvo:</strong> {version_value}<br>",
                    f"<strong>Revision:</strong> <code>{revision}</code>{run_line}</p>",
                    f"<pre>{config}</pre>",
                    "</article>",
                ]
            )
        )
    if not cards:
        return ""
    return "<section><h2>Reproducibility manifests</h2>" + "".join(cards) + "</section>"


def render_html_report(
    *,
    summary: str | Path | None = None,
    history: str | Path | None = None,
    sweep: str | Path | None = None,
    efficiency: str | Path | None = None,
    manifests: Iterable[str | Path] = (),
    title: str = "BoundEvo Experiment Report",
) -> str:
    """Render a self-contained HTML report from available result artifacts."""

    summary_path = Path(summary) if summary is not None else None
    history_path = Path(history) if history is not None else None
    sweep_path = Path(sweep) if sweep is not None else None
    efficiency_path = Path(efficiency) if efficiency is not None else None
    manifest_paths = [Path(path) for path in manifests]

    available = [
        path
        for path in (summary_path, history_path, sweep_path, efficiency_path)
        if path is not None and path.exists()
    ]
    if not available and not any(path.exists() for path in manifest_paths):
        raise ValueError("no report input artifacts were found")

    sections = []
    if summary_path is not None and summary_path.exists():
        sections.append(_rank_section(summary_path, "CEC2017 benchmark ranking"))
        sections.append(_runtime_section(summary_path, "CEC2017 operational summary"))
    if history_path is not None and history_path.exists():
        sections.append(_convergence_section(history_path))
    if sweep_path is not None and sweep_path.exists():
        sections.append(_rank_section(sweep_path, "Parent-count sweep ranking"))
        sections.append(_runtime_section(sweep_path, "Parent-count sweep operations"))
        sections.append(_sensitivity_section(sweep_path))
    if efficiency_path is not None and efficiency_path.exists():
        sections.append(_efficiency_section(efficiency_path))
    sections.append(_manifest_section(manifest_paths))

    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<style>
:root {{ color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
body {{ max-width: 1220px; margin: 0 auto; padding: 40px 24px 72px; line-height: 1.55; }}
header {{ border-bottom: 1px solid #8885; margin-bottom: 32px; padding-bottom: 18px; }}
h1 {{ margin: 0 0 8px; font-size: 2.2rem; }}
h2 {{ margin-top: 0; }}
section {{ margin: 24px 0; padding: 22px; border: 1px solid #8885; border-radius: 14px; }}
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
th, td {{ text-align: right; padding: 9px 12px; border-bottom: 1px solid #8884; }}
th:first-child, td:first-child {{ text-align: left; }}
code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
pre {{ overflow-x: auto; padding: 14px; border: 1px solid #8885; border-radius: 10px; }}
.manifest {{ margin-top: 16px; padding-top: 8px; }}
.muted {{ opacity: .72; }}
.chart {{ width: 100%; min-width: 620px; display: block; }}
.chart-card {{ overflow-x: auto; border-top: 1px solid #8884; padding-top: 8px; margin-top: 18px; }}
.chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(520px, 1fr)); gap: 18px; }}
.axis {{ stroke: currentColor; stroke-width: 1; opacity: .65; }}
.grid {{ stroke: currentColor; stroke-width: .7; opacity: .12; }}
.tick {{ fill: currentColor; font-size: 11px; opacity: .72; }}
.legend {{ fill: currentColor; font-size: 12px; }}
.axis-label {{ fill: currentColor; font-size: 12px; font-weight: 600; }}
</style>
</head>
<body>
<header>
<h1>{safe_title}</h1>
<p class="muted">Generated from BoundEvo CSV outputs and run manifests.</p>
</header>
{''.join(sections)}
</body>
</html>
"""


def write_html_report(path: str | Path, report: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
