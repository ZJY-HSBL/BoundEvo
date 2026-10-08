"""Standalone HTML reporting for BoundEvo experiment artifacts."""

from __future__ import annotations

import csv
import html
import json
import statistics
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .analysis import load_summary_metric, rank_methods, win_tie_loss


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
    return "".join(
        [
            "<section><h2>Coefficient-generation efficiency</h2>",
            "<p>Summary of the M-versus-efficiency experiment.</p>",
            _table(
                ["Method", "M points", "Mean efficiency", "Largest M", "Efficiency at largest M"],
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
        config = html.escape(
            json.dumps(payload.get("config", {}), indent=2, ensure_ascii=False)
        )
        cards.append(
            "".join(
                [
                    '<article class="manifest">',
                    f"<h3>{command}</h3>",
                    f"<p><strong>Created:</strong> {created}<br>",
                    f"<strong>BoundEvo:</strong> {version_value}<br>",
                    f"<strong>Revision:</strong> <code>{revision}</code></p>",
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
    sweep: str | Path | None = None,
    efficiency: str | Path | None = None,
    manifests: Iterable[str | Path] = (),
    title: str = "BoundEvo Experiment Report",
) -> str:
    """Render a self-contained HTML report from available result artifacts."""

    summary_path = Path(summary) if summary is not None else None
    sweep_path = Path(sweep) if sweep is not None else None
    efficiency_path = Path(efficiency) if efficiency is not None else None
    manifest_paths = [Path(path) for path in manifests]

    available = [
        path
        for path in (summary_path, sweep_path, efficiency_path)
        if path is not None and path.exists()
    ]
    if not available and not any(path.exists() for path in manifest_paths):
        raise ValueError("no report input artifacts were found")

    sections = []
    if summary_path is not None and summary_path.exists():
        sections.append(_rank_section(summary_path, "CEC2017 benchmark ranking"))
        sections.append(_runtime_section(summary_path, "CEC2017 operational summary"))
    if sweep_path is not None and sweep_path.exists():
        sections.append(_rank_section(sweep_path, "Parent-count sweep ranking"))
        sections.append(_runtime_section(sweep_path, "Parent-count sweep operations"))
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
body {{ max-width: 1180px; margin: 0 auto; padding: 40px 24px 72px; line-height: 1.55; }}
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
