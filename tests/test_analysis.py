import csv
from pathlib import Path

import pytest

from boundevo.analysis import (
    MetricObservation,
    load_summary_metric,
    rank_methods,
    render_analysis_report,
    win_tie_loss,
)


def _observations() -> list[MetricObservation]:
    return [
        MetricObservation("F1/D10", "abc", 1.0),
        MetricObservation("F1/D10", "edbf", 2.0),
        MetricObservation("F1/D10", "re", 3.0),
        MetricObservation("F3/D10", "abc", 2.0),
        MetricObservation("F3/D10", "edbf", 2.0),
        MetricObservation("F3/D10", "re", 4.0),
        MetricObservation("F4/D10", "abc", 4.0),
        MetricObservation("F4/D10", "edbf", 3.0),
        MetricObservation("F4/D10", "re", 5.0),
    ]


def test_rank_methods_uses_average_tie_ranks() -> None:
    rows = rank_methods(_observations(), methods=("abc", "edbf", "re"))
    by_method = {row.method: row for row in rows}
    assert by_method["abc"].mean_rank == pytest.approx((1.0 + 1.5 + 2.0) / 3)
    assert by_method["edbf"].mean_rank == pytest.approx((2.0 + 1.5 + 1.0) / 3)
    assert by_method["re"].mean_rank == 3.0


def test_win_tie_loss() -> None:
    row = win_tie_loss(_observations(), "abc", "edbf")
    assert (row.wins, row.ties, row.losses, row.cases) == (1, 1, 1, 3)


def test_load_summary_metric_includes_parent_count_when_present(tmp_path: Path) -> None:
    path = tmp_path / "summary.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("function_id", "dimension", "parent_count", "method", "mean_error"),
        )
        writer.writeheader()
        writer.writerow(
            {
                "function_id": 1,
                "dimension": 10,
                "parent_count": 15,
                "method": "abc",
                "mean_error": 0.25,
            }
        )
    row = load_summary_metric(path)[0]
    assert row.case == "F1/D10/M15"
    assert row.value == 0.25


def test_render_analysis_report() -> None:
    pytest.importorskip("scipy")
    report = render_analysis_report(
        _observations(),
        metric="mean_error",
        reference="abc",
        methods=("abc", "edbf", "re"),
    )
    assert "Mean ranks" in report
    assert "Win / Tie / Loss" in report
    assert "Wilcoxon signed-rank tests" in report
    assert "Friedman test" in report
