"""Run the source-aligned M=10..16 CEC2017 parent-count sweep."""

from __future__ import annotations

import argparse
from pathlib import Path

from boundevo.sweep import (
    PAPER_PARENT_COUNTS,
    PAPER_SWEEP_FUNCTION_IDS,
    run_parent_count_sweep,
    summarize_parent_sweep,
    write_parent_sweep_summary_csv,
    write_parent_sweep_trials_csv,
    write_source_style_tables,
)


def _parse_int_set(value: str) -> tuple[int, ...]:
    text = value.strip().lower()
    if text == "paper":
        raise ValueError("'paper' must be resolved by the caller")
    values: list[int] = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", maxsplit=1)
            start, end = int(start_text), int(end_text)
            step = 1 if end >= start else -1
            values.extend(range(start, end + step, step))
        else:
            values.append(int(token))
    if not values:
        raise ValueError("expected at least one integer")
    return tuple(values)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--functions",
        default="paper",
        help='Comma/range list, or "paper" for F1,F10,F20,F30.',
    )
    parser.add_argument(
        "--parents",
        default="10-16",
        help='Comma/range list of M values; source sweep is "10-16".',
    )
    parser.add_argument("--dimension", type=int, default=10)
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=("re", "edbf", "abc"),
        default=("re", "edbf", "abc"),
    )
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--evaluations", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/parent_sweep_trials.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/parent_sweep_summary.csv"),
    )
    parser.add_argument(
        "--tables",
        type=Path,
        default=Path("results/parent_sweep_tables.md"),
    )
    args = parser.parse_args()

    function_ids = (
        PAPER_SWEEP_FUNCTION_IDS
        if args.functions.strip().lower() == "paper"
        else _parse_int_set(args.functions)
    )
    parent_counts = (
        PAPER_PARENT_COUNTS
        if args.parents.strip().lower() == "paper"
        else _parse_int_set(args.parents)
    )
    records = run_parent_count_sweep(
        function_ids=function_ids,
        parent_counts=parent_counts,
        dimension=args.dimension,
        methods=tuple(args.methods),
        repeats=args.repeats,
        base_seed=args.seed,
        max_evaluations=args.evaluations,
    )
    summary = summarize_parent_sweep(records)
    write_parent_sweep_trials_csv(args.output, records)
    write_parent_sweep_summary_csv(args.summary, summary)
    write_source_style_tables(args.tables, summary)
    print(f"wrote {len(records)} trials to {args.output}")
    print(f"wrote {len(summary)} summary rows to {args.summary}")
    print(f"wrote source-style tables to {args.tables}")


if __name__ == "__main__":
    main()
