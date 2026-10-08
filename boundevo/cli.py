"""Command-line interface for reproducible BoundEvo experiments."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .analysis import load_summary_metric, render_analysis_report, write_analysis_report
from .cec2017 import PAPER_FUNCTION_IDS
from .config import int_selection, load_json_config, string_selection
from .efficiency import estimate_efficiency, write_efficiency_csv
from .experiments import (
    HistoryRecord,
    run_cec2017_suite,
    summarize,
    write_history_csv,
    write_summary_csv,
    write_trials_csv,
)
from .pipeline import PipelineConfig, run_pipeline
from .report import render_html_report, write_html_report
from .reproducibility import capture_manifest, write_manifest
from .runs import generate_run_id
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


def _coalesce(cli_value, config: dict, key: str, default):
    return cli_value if cli_value is not None else config.get(key, default)


def _resolved_run_id(args: argparse.Namespace, command: str) -> str:
    return args.run_id or generate_run_id(command)


def _write_run_manifest(
    path: Path,
    *,
    command: str,
    run_id: str,
    config: dict,
    outputs: dict[str, Path],
) -> None:
    write_manifest(
        path,
        capture_manifest(
            command=command,
            config=config,
            outputs=outputs,
            run_id=run_id,
        ),
    )
    print(f"run id: {run_id}")
    print(f"wrote run manifest to {path}")


def _benchmark(args: argparse.Namespace) -> None:
    cfg = load_json_config(args.config)
    run_id = _resolved_run_id(args, "benchmark")
    function_ids = int_selection(cfg.get("function_ids"), preset=PAPER_FUNCTION_IDS)
    methods = string_selection(cfg.get("methods"), default=("re", "edbf", "abc"))
    dimension = int(_coalesce(args.dimension, cfg, "dimension", 10))
    repeats = int(_coalesce(args.repeats, cfg, "repeats", 1))
    evaluations = int(_coalesce(args.evaluations, cfg, "max_evaluations", 100_000))
    seed = int(_coalesce(args.seed, cfg, "base_seed", 42))
    history_interval = int(
        _coalesce(args.history_interval, cfg, "history_interval", 100)
    )
    output = Path(_coalesce(args.output, cfg, "output", "results/cec2017_trials.csv"))
    summary_path = Path(
        _coalesce(args.summary, cfg, "summary", "results/cec2017_summary.csv")
    )
    history_path = Path(
        _coalesce(args.history, cfg, "history", "results/cec2017_history.csv")
    )
    manifest_path = Path(
        _coalesce(args.manifest, cfg, "manifest", "results/cec2017_manifest.json")
    )

    history: list[HistoryRecord] = []
    records = run_cec2017_suite(
        function_ids=function_ids,
        dimension=dimension,
        methods=methods,
        repeats=repeats,
        base_seed=seed,
        max_evaluations=evaluations,
        history_records=history,
        history_interval=history_interval,
    )
    rows = summarize(records)
    write_trials_csv(output, records)
    write_summary_csv(summary_path, rows)
    write_history_csv(history_path, history)
    _write_run_manifest(
        manifest_path,
        command="benchmark",
        run_id=run_id,
        config={
            "function_ids": function_ids,
            "dimension": dimension,
            "methods": methods,
            "repeats": repeats,
            "base_seed": seed,
            "max_evaluations": evaluations,
            "history_interval": history_interval,
        },
        outputs={"trials": output, "summary": summary_path, "history": history_path},
    )
    print(f"wrote {len(records)} trials to {output}")
    print(f"wrote {len(rows)} summary rows to {summary_path}")
    print(f"wrote {len(history)} sampled history rows to {history_path}")


def _sweep(args: argparse.Namespace) -> None:
    cfg = load_json_config(args.config)
    run_id = _resolved_run_id(args, "sweep")
    function_ids = int_selection(
        cfg.get("function_ids"),
        preset=PAPER_SWEEP_FUNCTION_IDS,
    )
    parent_counts = int_selection(
        cfg.get("parent_counts"),
        preset=PAPER_PARENT_COUNTS,
    )
    methods = string_selection(cfg.get("methods"), default=("re", "edbf", "abc"))
    dimension = int(_coalesce(args.dimension, cfg, "dimension", 10))
    repeats = int(_coalesce(args.repeats, cfg, "repeats", 1))
    evaluations = int(_coalesce(args.evaluations, cfg, "max_evaluations", 100_000))
    seed = int(_coalesce(args.seed, cfg, "base_seed", 42))
    history_interval = int(
        _coalesce(args.history_interval, cfg, "history_interval", 100)
    )
    output = Path(_coalesce(args.output, cfg, "output", "results/parent_sweep_trials.csv"))
    summary_path = Path(
        _coalesce(args.summary, cfg, "summary", "results/parent_sweep_summary.csv")
    )
    history_path = Path(
        _coalesce(args.history, cfg, "history", "results/parent_sweep_history.csv")
    )
    tables = Path(
        _coalesce(args.tables, cfg, "tables", "results/parent_sweep_tables.md")
    )
    manifest_path = Path(
        _coalesce(args.manifest, cfg, "manifest", "results/parent_sweep_manifest.json")
    )

    history: list[ParentSweepHistory] = []
    records = run_parent_count_sweep(
        function_ids=function_ids,
        parent_counts=parent_counts,
        dimension=dimension,
        methods=methods,
        repeats=repeats,
        base_seed=seed,
        max_evaluations=evaluations,
        history_records=history,
        history_interval=history_interval,
    )
    rows = summarize_parent_sweep(records)
    write_parent_sweep_trials_csv(output, records)
    write_parent_sweep_summary_csv(summary_path, rows)
    write_parent_sweep_history_csv(history_path, history)
    write_source_style_tables(tables, rows)
    _write_run_manifest(
        manifest_path,
        command="sweep",
        run_id=run_id,
        config={
            "function_ids": function_ids,
            "parent_counts": parent_counts,
            "dimension": dimension,
            "methods": methods,
            "repeats": repeats,
            "base_seed": seed,
            "max_evaluations": evaluations,
            "history_interval": history_interval,
        },
        outputs={
            "trials": output,
            "summary": summary_path,
            "history": history_path,
            "tables": tables,
        },
    )
    print(f"wrote {len(records)} trials to {output}")
    print(f"wrote {len(rows)} summary rows to {summary_path}")
    print(f"wrote {len(history)} sampled history rows to {history_path}")
    print(f"wrote source-style tables to {tables}")


def _efficiency(args: argparse.Namespace) -> None:
    cfg = load_json_config(args.config)
    run_id = _resolved_run_id(args, "efficiency")
    min_m = int(_coalesce(args.min_m, cfg, "min_m", 1))
    max_m = int(_coalesce(args.max_m, cfg, "max_m", 20))
    trials = int(_coalesce(args.trials, cfg, "trials", 1_000_000))
    batch_size = int(_coalesce(args.batch_size, cfg, "batch_size", 100_000))
    seed = int(_coalesce(args.seed, cfg, "seed", 42))
    methods = string_selection(cfg.get("methods"), default=("re", "edbf", "abc"))
    output = Path(
        _coalesce(args.output, cfg, "output", "results/coefficient_efficiency.csv")
    )
    manifest_path = Path(
        _coalesce(
            args.manifest,
            cfg,
            "manifest",
            "results/coefficient_efficiency_manifest.json",
        )
    )
    if min_m < 1 or max_m < min_m:
        raise ValueError("require 1 <= min_m <= max_m")

    rows = []
    for parent_count in range(min_m, max_m + 1):
        for method_index, method in enumerate(methods):
            rows.append(
                estimate_efficiency(
                    parent_count,
                    method=method,
                    trials=trials,
                    seed=seed + parent_count * 10 + method_index,
                    batch_size=batch_size,
                )
            )

    write_efficiency_csv(output, rows)
    _write_run_manifest(
        manifest_path,
        command="efficiency",
        run_id=run_id,
        config={
            "min_m": min_m,
            "max_m": max_m,
            "methods": methods,
            "trials": trials,
            "batch_size": batch_size,
            "seed": seed,
        },
        outputs={"efficiency": output},
    )
    print(f"wrote {len(rows)} rows to {output}")


def _analyze(args: argparse.Namespace) -> None:
    cfg = load_json_config(args.config)
    run_id = _resolved_run_id(args, "analyze")
    summary_path = Path(
        _coalesce(args.summary, cfg, "summary", "results/cec2017_summary.csv")
    )
    metric = str(_coalesce(args.metric, cfg, "metric", "mean_error"))
    reference = str(_coalesce(args.reference, cfg, "reference", "abc"))
    output = Path(
        _coalesce(args.output, cfg, "output", "results/statistical_analysis.md")
    )
    manifest_path = Path(
        _coalesce(args.manifest, cfg, "manifest", "results/analysis_manifest.json")
    )
    methods_value = args.methods if args.methods is not None else cfg.get("methods")
    methods = None
    if methods_value is not None:
        methods = string_selection(methods_value, default=("re", "edbf", "abc"))

    observations = load_summary_metric(summary_path, metric=metric)
    try:
        report = render_analysis_report(
            observations,
            metric=metric,
            reference=reference,
            methods=methods,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    write_analysis_report(output, report)
    _write_run_manifest(
        manifest_path,
        command="analyze",
        run_id=run_id,
        config={
            "summary": summary_path,
            "metric": metric,
            "reference": reference,
            "methods": methods,
        },
        outputs={"analysis": output},
    )
    print(report)
    print(f"wrote statistical report to {output}")


def _report(args: argparse.Namespace) -> None:
    cfg = load_json_config(args.config)
    run_id = _resolved_run_id(args, "report")
    summary = Path(
        _coalesce(args.summary, cfg, "summary", "results/cec2017_summary.csv")
    )
    history = Path(
        _coalesce(args.history, cfg, "history", "results/cec2017_history.csv")
    )
    sweep = Path(
        _coalesce(args.sweep, cfg, "sweep", "results/parent_sweep_summary.csv")
    )
    efficiency = Path(
        _coalesce(
            args.efficiency,
            cfg,
            "efficiency",
            "results/coefficient_efficiency.csv",
        )
    )
    output = Path(_coalesce(args.output, cfg, "output", "results/report.html"))
    manifest_path = Path(
        _coalesce(args.manifest, cfg, "manifest", "results/report_manifest.json")
    )
    title = str(_coalesce(args.title, cfg, "title", "BoundEvo Experiment Report"))

    default_manifests = [
        "results/cec2017_manifest.json",
        "results/parent_sweep_manifest.json",
        "results/coefficient_efficiency_manifest.json",
        "results/analysis_manifest.json",
    ]
    manifest_values = args.manifests if args.manifests is not None else cfg.get("manifests")
    if manifest_values is None:
        manifests = [Path(value) for value in default_manifests]
    elif isinstance(manifest_values, str):
        manifests = [Path(manifest_values)]
    else:
        manifests = [Path(value) for value in manifest_values]

    report = render_html_report(
        summary=summary,
        history=history,
        sweep=sweep,
        efficiency=efficiency,
        manifests=manifests,
        title=title,
    )
    write_html_report(output, report)
    _write_run_manifest(
        manifest_path,
        command="report",
        run_id=run_id,
        config={
            "summary": summary,
            "history": history,
            "sweep": sweep,
            "efficiency": efficiency,
            "manifests": manifests,
            "title": title,
        },
        outputs={"report": output},
    )
    print(f"wrote standalone HTML report to {output}")


def _pipeline(args: argparse.Namespace) -> None:
    cfg = load_json_config(args.config)
    function_ids = int_selection(cfg.get("function_ids"), preset=PAPER_FUNCTION_IDS)
    sweep_function_ids = int_selection(
        cfg.get("sweep_function_ids"),
        preset=PAPER_SWEEP_FUNCTION_IDS,
    )
    parent_counts = int_selection(
        cfg.get("parent_counts"),
        preset=PAPER_PARENT_COUNTS,
    )
    methods = string_selection(cfg.get("methods"), default=("re", "edbf", "abc"))
    run_root = Path(_coalesce(args.run_root, cfg, "run_root", "results/runs"))
    pipeline_config = PipelineConfig(
        function_ids=function_ids,
        sweep_function_ids=sweep_function_ids,
        parent_counts=parent_counts,
        dimension=int(_coalesce(args.dimension, cfg, "dimension", 10)),
        methods=methods,
        repeats=int(_coalesce(args.repeats, cfg, "repeats", 1)),
        base_seed=int(_coalesce(args.seed, cfg, "base_seed", 42)),
        max_evaluations=int(
            _coalesce(args.evaluations, cfg, "max_evaluations", 100_000)
        ),
        history_interval=int(
            _coalesce(args.history_interval, cfg, "history_interval", 100)
        ),
        efficiency_min_m=int(cfg.get("efficiency_min_m", 1)),
        efficiency_max_m=int(cfg.get("efficiency_max_m", 20)),
        efficiency_trials=int(cfg.get("efficiency_trials", 1_000_000)),
        efficiency_batch_size=int(cfg.get("efficiency_batch_size", 100_000)),
        run_root=run_root,
        report_title=str(cfg.get("report_title", "BoundEvo Experiment Report")),
        statistical_analysis=bool(cfg.get("statistical_analysis", True)),
    )
    try:
        result = run_pipeline(pipeline_config, run_id=args.run_id)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"pipeline run id: {result.run_id}")
    print(f"run directory: {result.run_dir}")
    print(f"report: {result.report}")


def _add_common_run_overrides(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dimension", type=int)
    parser.add_argument("--repeats", type=int)
    parser.add_argument("--evaluations", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--history", type=Path)
    parser.add_argument("--history-interval", type=int)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--run-id")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="boundevo",
        description="Adaptive-boundary multi-parent evolutionary optimization.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    benchmark = subparsers.add_parser("benchmark", help="run the CEC2017 benchmark matrix")
    _add_common_run_overrides(benchmark)
    benchmark.set_defaults(func=_benchmark)

    sweep = subparsers.add_parser("sweep", help="run the parent-count sweep")
    _add_common_run_overrides(sweep)
    sweep.add_argument("--tables", type=Path)
    sweep.set_defaults(func=_sweep)

    efficiency = subparsers.add_parser(
        "efficiency",
        help="estimate coefficient-generation efficiency versus parent count",
    )
    efficiency.add_argument("--config", type=Path)
    efficiency.add_argument("--min-m", type=int)
    efficiency.add_argument("--max-m", type=int)
    efficiency.add_argument("--trials", type=int)
    efficiency.add_argument("--batch-size", type=int)
    efficiency.add_argument("--seed", type=int)
    efficiency.add_argument("--output", type=Path)
    efficiency.add_argument("--manifest", type=Path)
    efficiency.add_argument("--run-id")
    efficiency.set_defaults(func=_efficiency)

    analyze = subparsers.add_parser(
        "analyze",
        help="rank methods and run W/T/L, Wilcoxon, and Friedman tests",
    )
    analyze.add_argument("--config", type=Path)
    analyze.add_argument("--summary", type=Path)
    analyze.add_argument("--metric")
    analyze.add_argument("--reference")
    analyze.add_argument("--methods", nargs="+")
    analyze.add_argument("--output", type=Path)
    analyze.add_argument("--manifest", type=Path)
    analyze.add_argument("--run-id")
    analyze.set_defaults(func=_analyze)

    report = subparsers.add_parser(
        "report",
        help="build a standalone HTML report from experiment artifacts",
    )
    report.add_argument("--config", type=Path)
    report.add_argument("--summary", type=Path)
    report.add_argument("--history", type=Path)
    report.add_argument("--sweep", type=Path)
    report.add_argument("--efficiency", type=Path)
    report.add_argument("--manifests", nargs="*")
    report.add_argument("--title")
    report.add_argument("--output", type=Path)
    report.add_argument("--manifest", type=Path)
    report.add_argument("--run-id")
    report.set_defaults(func=_report)

    pipeline = subparsers.add_parser(
        "pipeline",
        help="run the complete experiment suite in a unique managed run directory",
    )
    pipeline.add_argument("--config", type=Path)
    pipeline.add_argument("--run-id")
    pipeline.add_argument("--run-root", type=Path)
    pipeline.add_argument("--dimension", type=int)
    pipeline.add_argument("--repeats", type=int)
    pipeline.add_argument("--evaluations", type=int)
    pipeline.add_argument("--history-interval", type=int)
    pipeline.add_argument("--seed", type=int)
    pipeline.set_defaults(func=_pipeline)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except (TypeError, ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
