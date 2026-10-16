"""Tests for the read-only run registry and cross-run Pareto comparison."""

import csv
import json
from pathlib import Path

import pytest

from boundevo.cli import main
from boundevo.comparison import (
    compare_runs,
    pareto_indices,
    render_comparison_markdown,
    write_comparison_report,
)
from boundevo.registry import read_benchmark_metrics, scan_runs


def _create_run(
    root: Path,
    run_id: str,
    *,
    metrics: list[tuple[int, int, str, float, float, float]],
    budget: int = 500,
    platform: str = "Linux",
    source_revision: str = "same-revision",
) -> Path:
    directory = root / run_id
    (directory / "benchmark").mkdir(parents=True)
    (directory / "report").mkdir()
    (directory / "report" / "report.html").write_text("report", encoding="utf-8")
    manifest = {
        "run_id": run_id,
        "command": "pipeline",
        "created_at_utc": "2026-10-16T00:00:00Z",
        "boundevo_version": "0.5.0.dev0",
        "platform": platform,
        "source_revision": source_revision,
        "config": {
            "dimension": 10,
            "methods": ["abc", "re"],
            "function_ids": [1, 3],
            "max_evaluations": budget,
            "repeats": 2,
        },
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with (directory / "benchmark" / "summary.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "function_id",
                "dimension",
                "method",
                "mean_error",
                "mean_elapsed_seconds",
                "mean_evaluations",
            ]
        )
        writer.writerows(metrics)
    return directory


def _base_rows(error: float, runtime: float, evaluations: float):
    return [
        (1, 10, "abc", error, runtime, evaluations),
        (3, 10, "abc", error * 2, runtime * 2, evaluations * 2),
    ]


def test_registry_handles_complete_incomplete_invalid(tmp_path: Path) -> None:
    _create_run(tmp_path, "good", metrics=_base_rows(1, 1, 100))
    (tmp_path / "unfinished").mkdir()
    bad = tmp_path / "invalid"
    bad.mkdir()
    (bad / "manifest.json").write_text("{not-json", encoding="utf-8")

    entries = {entry.run_id: entry for entry in scan_runs(tmp_path)}
    assert entries["good"].status == "complete"
    assert entries["good"].dimension == 10
    assert entries["good"].evaluation_budget == 500
    assert entries["unfinished"].status == "incomplete"
    assert entries["invalid"].status == "invalid"
    assert entries["good"].to_dict()["directory"].endswith("good")
    assert scan_runs(tmp_path / "does-not-exist") == []


def test_registry_never_follows_manifest_output_paths(tmp_path: Path) -> None:
    outside = tmp_path / "outside.csv"
    outside.write_text("secret", encoding="utf-8")
    directory = _create_run(tmp_path, "run-a", metrics=_base_rows(1, 1, 100))
    manifest_path = directory / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["outputs"] = {"summary": str(outside)}
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    entry = next(item for item in scan_runs(tmp_path) if item.run_id == "run-a")
    metrics = read_benchmark_metrics(entry)
    assert len(metrics) == 2
    assert metrics[(1, 10, "abc")].mean_error == 1.0


def test_compare_reports_criterion_winners_and_nondominated(tmp_path: Path) -> None:
    _create_run(tmp_path, "accurate", metrics=_base_rows(1, 3, 300))
    _create_run(tmp_path, "fast", metrics=_base_rows(2, 1, 100))
    _create_run(tmp_path, "dominated", metrics=_base_rows(4, 5, 500))

    comparison = compare_runs(tmp_path)
    assert len(comparison.cases) == 2
    assert comparison.best_error_run == "accurate"
    assert comparison.fastest_run == "fast"
    assert comparison.fewest_evaluations_run == "fast"
    assert set(comparison.pareto_run_ids) == {"accurate", "fast"}
    assert not next(
        row for row in comparison.scores if row.run_id == "dominated"
    ).pareto_efficient
    report = render_comparison_markdown(comparison)
    assert "There is no single automatically best overall run" in report

    destination = tmp_path / "comparison.md"
    write_comparison_report(destination, comparison)
    assert destination.read_text(encoding="utf-8") == report


def test_compare_rejects_case_mismatch_unless_opted_in(tmp_path: Path) -> None:
    _create_run(tmp_path, "a", metrics=_base_rows(1, 2, 150))
    _create_run(tmp_path, "b", metrics=[(1, 10, "abc", 0.5, 4, 300)])

    with pytest.raises(ValueError, match="benchmark case sets differ"):
        compare_runs(tmp_path)
    result = compare_runs(tmp_path, allow_partial=True)
    assert result.cases == ((1, 10, "abc"),)
    assert any("Partial coverage" in message for message in result.warnings)


def test_mixed_budgets_and_platforms_warn(tmp_path: Path) -> None:
    _create_run(tmp_path, "a", metrics=_base_rows(1, 3, 200))
    _create_run(
        tmp_path,
        "b",
        metrics=_base_rows(2, 4, 350),
        budget=800,
        platform="Windows",
        source_revision="different-revision",
    )
    result = compare_runs(tmp_path)
    joined = " ".join(result.warnings)
    assert "Evaluation budgets differ" in joined
    assert "Runtime comparisons" in joined
    assert "Source revisions differ" in joined


def test_duplicate_or_invalid_summary_rows_are_rejected(tmp_path: Path) -> None:
    _create_run(tmp_path, "a", metrics=_base_rows(1, 2, 100))
    entry = scan_runs(tmp_path)[0]
    summary = entry.directory / "benchmark" / "summary.csv"
    with summary.open("a", encoding="utf-8") as handle:
        handle.write("1,10,abc,2,2,100\n")
    with pytest.raises(ValueError, match="duplicate"):
        read_benchmark_metrics(entry)


def test_pareto_ties_and_dominance() -> None:
    assert pareto_indices([(1, 3), (3, 1), (2, 4), (1, 3)]) == (0, 1, 3)
    with pytest.raises(ValueError, match="finite"):
        pareto_indices([(1.0, float("nan"))])


def test_cli_runs_and_compare(tmp_path: Path, capsys, monkeypatch) -> None:
    _create_run(tmp_path, "a", metrics=_base_rows(1, 2, 200))
    _create_run(tmp_path, "b", metrics=_base_rows(2, 1, 100))
    monkeypatch.setattr(
        "sys.argv",
        ["boundevo", "runs", "--root", str(tmp_path), "--json"],
    )
    main()
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 2

    monkeypatch.setattr(
        "sys.argv",
        [
            "boundevo",
            "compare",
            "--root",
            str(tmp_path),
            "--run-id",
            "a",
            "--run-id",
            "b",
        ],
    )
    main()
    assert "Pareto" in capsys.readouterr().out
