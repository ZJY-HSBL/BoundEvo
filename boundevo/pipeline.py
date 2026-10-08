"""End-to-end managed experiment pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .analysis import load_summary_metric, render_analysis_report, write_analysis_report
from .cec2017 import PAPER_FUNCTION_IDS
from .coefficients import Method
from .efficiency import EfficiencyPoint, estimate_efficiency, write_efficiency_csv
from .experiments import (
    HistoryRecord,
    run_cec2017_suite,
    summarize,
    write_history_csv,
    write_summary_csv,
    write_trials_csv,
)
from .report import render_html_report, write_html_report
from .reproducibility import capture_manifest, write_manifest
from .runs import RunDirectory, create_run_directory
from .sweep import (
    PAPER_PARENT_COUNTS,
    PAPER_SWEEP_FUNCTION_IDS,
    ParentSweepHistory,
    run_parent_count_sweep,
    summarize_parent_sweep,
    write_parent_sweep_history_csv,
    write_parent_sweep_summary_csv,
    write_parent_sweep_trials_csv,
    write_source_style_tables,
)


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    function_ids: tuple[int, ...] = PAPER_FUNCTION_IDS
    sweep_function_ids: tuple[int, ...] = PAPER_SWEEP_FUNCTION_IDS
    parent_counts: tuple[int, ...] = PAPER_PARENT_COUNTS
    dimension: int = 10
    methods: tuple[Method, ...] = ("re", "edbf", "abc")
    repeats: int = 1
    base_seed: int = 42
    max_evaluations: int = 100_000
    history_interval: int = 100
    efficiency_min_m: int = 1
    efficiency_max_m: int = 20
    efficiency_trials: int = 1_000_000
    efficiency_batch_size: int = 100_000
    run_root: Path = Path("results/runs")
    report_title: str = "BoundEvo Experiment Report"
    statistical_analysis: bool = True

    def validate(self) -> None:
        if self.dimension < 2:
            raise ValueError("dimension must be at least 2")
        if self.repeats < 1:
            raise ValueError("repeats must be at least 1")
        if self.max_evaluations < 100:
            raise ValueError("max_evaluations must be at least the population size 100")
        if self.history_interval < 1:
            raise ValueError("history_interval must be at least 1")
        if self.statistical_analysis and len(self.methods) < 3:
            raise ValueError("pipeline statistical analysis requires at least three methods")
        if self.efficiency_min_m < 1 or self.efficiency_max_m < self.efficiency_min_m:
            raise ValueError("invalid efficiency parent-count range")
        if self.efficiency_trials < 1 or self.efficiency_batch_size < 1:
            raise ValueError("efficiency trial and batch sizes must be positive")


@dataclass(frozen=True, slots=True)
class PipelineResult:
    run_id: str
    run_dir: Path
    report: Path
    manifest: Path


def _stage_manifest(
    run: RunDirectory,
    *,
    path: Path,
    command: str,
    config: dict,
    outputs: dict[str, Path],
) -> None:
    write_manifest(
        path,
        capture_manifest(
            command=command,
            config=config,
            outputs=outputs,
            run_id=run.run_id,
        ),
    )


def run_pipeline(
    config: PipelineConfig | None = None,
    *,
    run_id: str | None = None,
) -> PipelineResult:
    """Run the full benchmark, sweep, efficiency, analysis, and report pipeline."""

    cfg = config or PipelineConfig()
    cfg.validate()
    run = create_run_directory(kind="experiment", root=cfg.run_root, run_id=run_id)

    benchmark_dir = run.file("benchmark")
    sweep_dir = run.file("sweep")
    efficiency_dir = run.file("efficiency")
    analysis_dir = run.file("analysis")
    report_dir = run.file("report")
    for directory in (benchmark_dir, sweep_dir, efficiency_dir, analysis_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    benchmark_history: list[HistoryRecord] = []
    benchmark_trials = run_cec2017_suite(
        function_ids=cfg.function_ids,
        dimension=cfg.dimension,
        methods=cfg.methods,
        repeats=cfg.repeats,
        base_seed=cfg.base_seed,
        max_evaluations=cfg.max_evaluations,
        history_records=benchmark_history,
        history_interval=cfg.history_interval,
    )
    benchmark_summary = summarize(benchmark_trials)
    benchmark_trials_path = benchmark_dir / "trials.csv"
    benchmark_summary_path = benchmark_dir / "summary.csv"
    benchmark_history_path = benchmark_dir / "history.csv"
    benchmark_manifest_path = benchmark_dir / "manifest.json"
    write_trials_csv(benchmark_trials_path, benchmark_trials)
    write_summary_csv(benchmark_summary_path, benchmark_summary)
    write_history_csv(benchmark_history_path, benchmark_history)
    _stage_manifest(
        run,
        path=benchmark_manifest_path,
        command="pipeline:benchmark",
        config={
            "function_ids": cfg.function_ids,
            "dimension": cfg.dimension,
            "methods": cfg.methods,
            "repeats": cfg.repeats,
            "base_seed": cfg.base_seed,
            "max_evaluations": cfg.max_evaluations,
            "history_interval": cfg.history_interval,
        },
        outputs={
            "trials": benchmark_trials_path,
            "summary": benchmark_summary_path,
            "history": benchmark_history_path,
        },
    )

    sweep_history: list[ParentSweepHistory] = []
    sweep_trials = run_parent_count_sweep(
        function_ids=cfg.sweep_function_ids,
        parent_counts=cfg.parent_counts,
        dimension=cfg.dimension,
        methods=cfg.methods,
        repeats=cfg.repeats,
        base_seed=cfg.base_seed,
        max_evaluations=cfg.max_evaluations,
        history_records=sweep_history,
        history_interval=cfg.history_interval,
    )
    sweep_summary = summarize_parent_sweep(sweep_trials)
    sweep_trials_path = sweep_dir / "trials.csv"
    sweep_summary_path = sweep_dir / "summary.csv"
    sweep_history_path = sweep_dir / "history.csv"
    sweep_tables_path = sweep_dir / "tables.md"
    sweep_manifest_path = sweep_dir / "manifest.json"
    write_parent_sweep_trials_csv(sweep_trials_path, sweep_trials)
    write_parent_sweep_summary_csv(sweep_summary_path, sweep_summary)
    write_parent_sweep_history_csv(sweep_history_path, sweep_history)
    write_source_style_tables(sweep_tables_path, sweep_summary)
    _stage_manifest(
        run,
        path=sweep_manifest_path,
        command="pipeline:sweep",
        config={
            "function_ids": cfg.sweep_function_ids,
            "parent_counts": cfg.parent_counts,
            "dimension": cfg.dimension,
            "methods": cfg.methods,
            "repeats": cfg.repeats,
            "base_seed": cfg.base_seed,
            "max_evaluations": cfg.max_evaluations,
            "history_interval": cfg.history_interval,
        },
        outputs={
            "trials": sweep_trials_path,
            "summary": sweep_summary_path,
            "history": sweep_history_path,
            "tables": sweep_tables_path,
        },
    )

    efficiency_rows: list[EfficiencyPoint] = []
    for parent_count in range(cfg.efficiency_min_m, cfg.efficiency_max_m + 1):
        for method_index, method in enumerate(cfg.methods):
            efficiency_rows.append(
                estimate_efficiency(
                    parent_count,
                    method=method,
                    trials=cfg.efficiency_trials,
                    seed=cfg.base_seed + parent_count * 10 + method_index,
                    batch_size=cfg.efficiency_batch_size,
                )
            )
    efficiency_path = efficiency_dir / "efficiency.csv"
    efficiency_manifest_path = efficiency_dir / "manifest.json"
    write_efficiency_csv(efficiency_path, efficiency_rows)
    _stage_manifest(
        run,
        path=efficiency_manifest_path,
        command="pipeline:efficiency",
        config={
            "min_m": cfg.efficiency_min_m,
            "max_m": cfg.efficiency_max_m,
            "methods": cfg.methods,
            "trials": cfg.efficiency_trials,
            "batch_size": cfg.efficiency_batch_size,
            "seed": cfg.base_seed,
        },
        outputs={"efficiency": efficiency_path},
    )

    analysis_path = analysis_dir / "statistical_analysis.md"
    analysis_manifest_path = analysis_dir / "manifest.json"
    report_manifests = [
        benchmark_manifest_path,
        sweep_manifest_path,
        efficiency_manifest_path,
    ]
    if cfg.statistical_analysis:
        observations = load_summary_metric(benchmark_summary_path, metric="mean_error")
        analysis_report = render_analysis_report(
            observations,
            metric="mean_error",
            reference="abc",
            methods=cfg.methods,
        )
        write_analysis_report(analysis_path, analysis_report)
        _stage_manifest(
            run,
            path=analysis_manifest_path,
            command="pipeline:analysis",
            config={
                "summary": benchmark_summary_path,
                "metric": "mean_error",
                "reference": "abc",
                "methods": cfg.methods,
            },
            outputs={"analysis": analysis_path},
        )
        report_manifests.append(analysis_manifest_path)

    report_path = report_dir / "report.html"
    report_manifest_path = report_dir / "manifest.json"
    html_report = render_html_report(
        summary=benchmark_summary_path,
        history=benchmark_history_path,
        sweep=sweep_summary_path,
        efficiency=efficiency_path,
        manifests=report_manifests,
        title=f"{cfg.report_title} — {run.run_id}",
    )
    write_html_report(report_path, html_report)
    _stage_manifest(
        run,
        path=report_manifest_path,
        command="pipeline:report",
        config={
            "summary": benchmark_summary_path,
            "history": benchmark_history_path,
            "sweep": sweep_summary_path,
            "efficiency": efficiency_path,
            "title": cfg.report_title,
        },
        outputs={"report": report_path},
    )

    pipeline_manifest_path = run.file("manifest.json")
    _stage_manifest(
        run,
        path=pipeline_manifest_path,
        command="pipeline",
        config={
            "function_ids": cfg.function_ids,
            "sweep_function_ids": cfg.sweep_function_ids,
            "parent_counts": cfg.parent_counts,
            "dimension": cfg.dimension,
            "methods": cfg.methods,
            "repeats": cfg.repeats,
            "base_seed": cfg.base_seed,
            "max_evaluations": cfg.max_evaluations,
            "history_interval": cfg.history_interval,
            "efficiency_min_m": cfg.efficiency_min_m,
            "efficiency_max_m": cfg.efficiency_max_m,
            "efficiency_trials": cfg.efficiency_trials,
            "efficiency_batch_size": cfg.efficiency_batch_size,
            "statistical_analysis": cfg.statistical_analysis,
        },
        outputs={
            "benchmark": benchmark_dir,
            "sweep": sweep_dir,
            "efficiency": efficiency_dir,
            "analysis": analysis_dir,
            "report": report_path,
        },
    )
    return PipelineResult(
        run_id=run.run_id,
        run_dir=run.path,
        report=report_path,
        manifest=pipeline_manifest_path,
    )
