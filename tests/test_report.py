import csv
import json
from pathlib import Path

from boundevo.report import render_html_report, write_html_report


def _write_summary(path: Path, *, sweep: bool = False) -> None:
    fields = [
        "function_id",
        "dimension",
        "method",
        "mean_error",
        "mean_elapsed_seconds",
        "mean_evaluations",
    ]
    if sweep:
        fields.insert(2, "parent_count")
    rows = []
    for function_id in (1, 3):
        for index, method in enumerate(("abc", "edbf", "re"), start=1):
            row = {
                "function_id": function_id,
                "dimension": 10,
                "method": method,
                "mean_error": float(index),
                "mean_elapsed_seconds": 0.1 * index,
                "mean_evaluations": 1000 * index,
            }
            if sweep:
                row["parent_count"] = 10
            rows.append(row)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_efficiency(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("parent_count", "method", "trials", "accepted", "efficiency"),
        )
        writer.writeheader()
        for parent_count in (1, 5):
            for method, efficiency in (("abc", 1.0), ("edbf", 0.7), ("re", 0.3)):
                writer.writerow(
                    {
                        "parent_count": parent_count,
                        "method": method,
                        "trials": 100,
                        "accepted": int(100 * efficiency),
                        "efficiency": efficiency,
                    }
                )


def test_render_standalone_report(tmp_path: Path) -> None:
    summary = tmp_path / "summary.csv"
    sweep = tmp_path / "sweep.csv"
    efficiency = tmp_path / "efficiency.csv"
    manifest = tmp_path / "manifest.json"
    _write_summary(summary)
    _write_summary(sweep, sweep=True)
    _write_efficiency(efficiency)
    manifest.write_text(
        json.dumps(
            {
                "command": "benchmark",
                "created_at_utc": "2026-10-08T00:00:00+00:00",
                "boundevo_version": "0.4.0.dev0",
                "source_revision": "abc123",
                "config": {"dimension": 10},
            }
        ),
        encoding="utf-8",
    )

    report = render_html_report(
        summary=summary,
        sweep=sweep,
        efficiency=efficiency,
        manifests=[manifest],
    )
    assert "<!doctype html>" in report
    assert "CEC2017 benchmark ranking" in report
    assert "Parent-count sweep ranking" in report
    assert "Coefficient-generation efficiency" in report
    assert "Reproducibility manifests" in report
    assert "abc vs edbf" in report

    output = tmp_path / "report.html"
    write_html_report(output, report)
    assert output.read_text(encoding="utf-8") == report
