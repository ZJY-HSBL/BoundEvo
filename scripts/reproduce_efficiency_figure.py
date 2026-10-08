"""Reproduce the coefficient-generation efficiency experiment for M=1..20."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from boundevo.efficiency import EfficiencyPoint, estimate_efficiency


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-m", type=int, default=1)
    parser.add_argument("--max-m", type=int, default=20)
    parser.add_argument("--trials", type=int, default=1_000_000)
    parser.add_argument("--batch-size", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/coefficient_efficiency.csv"),
    )
    args = parser.parse_args()

    if args.min_m < 1 or args.max_m < args.min_m:
        raise SystemExit("require 1 <= min-m <= max-m")

    rows: list[EfficiencyPoint] = []
    for parent_count in range(args.min_m, args.max_m + 1):
        for method_index, method in enumerate(("re", "edbf", "abc")):
            rows.append(
                estimate_efficiency(
                    parent_count,
                    method=method,
                    trials=args.trials,
                    seed=args.seed + parent_count * 10 + method_index,
                    batch_size=args.batch_size,
                )
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
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
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
