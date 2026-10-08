"""Command-line interface for reproducible BoundEvo experiments."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from . import __version__
from .analysis import load_summary_metric, render_analysis_report, write_analysis_report
from .cec2017 import PAPER_FUNCTION_IDS
from .config import int_selection, load_json_config, string_selection
from .efficiency import estimate_efficiency
from .experiments import run_cec2017_suite, summarize, write_summary_csv, write_trials_csv
from .sweep import (
    PAPER_PARENT_COUNTS,
    PAPER_SWEEP_FUNCTION_IDS,
    run_parent_count_sweep,
    summarize_parent_sweep,
    write_parent_sweep_summary_csv,
    write_parent_sweep_trials_csv,
    write_source_style_tables,
)


def _coalesce(cli_value, config: dict, key: str, default):
    return cli_value if cli_value is not None else config.get(key, default)


def _benchmark(args: argparse.Namespace) -> None:
    cfg = load_json_config(args.config)
    function_ids = int_selection(cfg.get("function_ids"), preset=PAPER_FUNCTION_IDS)
    methods = string_selection(cfg.get("methods"), default=("re", "edbf", "abc"))
    dimension = int(_coalesce(args.dimension, cfg, "dimension", 10))
    repeats = int(_coalesce(args.repeats, cfg, "repeats", 1))
    evaluations = int(_coalesce(args.evaluations, cfg, "max_evaluations", 100_000))
    seed = int(_coalesce(args.seed, cfg, "base_seed", 42))
    output = Path(_coalesce(args.output, cfg, "output", "results/cec2017_trials.csv"))
    summary_path = Path(
        _coalesce(args.summary, cfg, "summary", "results/cec2017_summary.csv")
    )

    records = run_cec2017_suite(
        function_ids=function_ids,
        dimension=dimension,
        methods=methods,
        repeats=repeats,
        base_seed=seed,
        max_evaluations=evaluations,
    )
    rows = summarize(records)
    write_trials_csv(output, records)
    write_summary_csv(summary_path, rows)
    print(f"wrote {len(records)} trials to {output}")
    print(f"wrote {len(rows)} summary rows to {summary_path}")


def _sweep(args: argparse.Namespace) -> None:
    cfg = load_json_config(args.config)
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
    output = Path(_coalesce(args.output, cfg, "output", "results/parent_sweep_trials.csv"))
    summary_path = Path(
        _coalesce(args.summary, cfg, "summary", "results/parent_sweep_summary.csv")
    )
    tables = Path(
        _coalesce(args.tables, cfg, "tables", "results/parent_sweep_tables.md")
    )

    records = run_parent_count_sweep(
        function_ids=function_ids,
        parent_counts=parent_counts,
        dimension=dimension,
        methods=methods,
        repeats=repeats,
        base_seed=seed,
        max_evaluations=evaluations,
    )
    rows = summarize_parent_sweep(records)
    write_parent_sweep_trials_csv(output, records)
    write_parent_sweep_summary_csv(summary_path, rows)
    write_source_style_tables(tables, rows)
    print(f"wrote {len(records)} trials to {output}")
    print(f"wrote {len(rows)} summary rows to {summary_path}")
    print(f"wrote source-style tables to {tables}")


def _efficiency(args: argparse.Namespace) -> None:
    cfg = load_json_config(args.config)
    min_m = int(_coalesce(args.min_m, cfg, "min_m", 1))
    max_m = int(_coalesce(args.max_m, cfg, "max_m", 20))
    trials = int(_coalesce(args.trials, cfg, "trials", 1_000_000))
    batch_size = int(_coalesce(args.batch_size, cfg, "batch_size", 100_000))
    seed = int(_coalesce(args.seed, cfg, "seed", 42))
    methods = string_selection(cfg.get("methods"), default=("re", "edbf", "abc"))
    output = Path(
        _coalesce(args.output, cfg, "output", "results/coefficient_efficiency.csv")
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

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("parent_count", "method", "trials", "accepted", "efficiency"),
        )
        writer.writeheader()
        writer.writerows(
            {
                "parent_count": row.parent_count,
                "method": row.method,
                "trials": row.trials,
                "accepted": row.accepted,
                "efficiency": row.efficiency,
            }
            for row in rows
        )
    print(f"wrote {len(rows)} rows to {output}")


def _analyze(args: argparse.Namespace) -> None:
    cfg = load_json_config(args.config)
    summary_path = Path(
        _coalesce(args.summary, cfg, "summary", "results/cec2017_summary.csv")
    )
    metric = str(_coalesce(args.metric, cfg, "metric", "mean_error"))
    reference = str(_coalesce(args.reference, cfg, "reference", "abc"))
    output = Path(
        _coalesce(args.output, cfg, "output", "results/statistical_analysis.md")
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
    print(report)
    print(f"wrote statistical report to {output}")


def _add_common_run_overrides(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dimension", type=int)
    parser.add_argument("--repeats", type=int)
    parser.add_argument("--evaluations", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", type=Path)


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
    analyze.set_defaults(func=_analyze)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
