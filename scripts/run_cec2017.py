"""Run the source-aligned CEC2017 benchmark matrix."""

from __future__ import annotations

import argparse
from pathlib import Path

from boundevo.cec2017 import PAPER_FUNCTION_IDS
from boundevo.experiments import (
    run_cec2017_suite,
    summarize,
    write_summary_csv,
    write_trials_csv,
)


def _parse_functions(value: str) -> tuple[int, ...]:
    if value.strip().lower() == "paper":
        return PAPER_FUNCTION_IDS
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--functions",
        default="paper",
        help='Comma-separated ids, or "paper" for F1 and F3..F30.',
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
    parser.add_argument("--output", type=Path, default=Path("results/cec2017_trials.csv"))
    parser.add_argument("--summary", type=Path, default=Path("results/cec2017_summary.csv"))
    args = parser.parse_args()

    records = run_cec2017_suite(
        function_ids=_parse_functions(args.functions),
        dimension=args.dimension,
        methods=tuple(args.methods),
        repeats=args.repeats,
        base_seed=args.seed,
        max_evaluations=args.evaluations,
    )
    summary = summarize(records)
    write_trials_csv(args.output, records)
    write_summary_csv(args.summary, summary)
    print(f"wrote {len(records)} trials to {args.output}")
    print(f"wrote {len(summary)} summary rows to {args.summary}")


if __name__ == "__main__":
    main()
