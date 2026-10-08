"""Plot mean CEC2017 objective error from a BoundEvo summary CSV."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "summary",
        type=Path,
        nargs="?",
        default=Path("results/cec2017_summary.csv"),
    )
    parser.add_argument("--output", type=Path, default=Path("results/cec2017_error.png"))
    args = parser.parse_args()

    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        raise SystemExit('plotting requires: pip install -e ".[plot]"') from exc

    grouped: dict[str, list[tuple[int, float]]] = defaultdict(list)
    with args.summary.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped[row["method"]].append((int(row["function_id"]), float(row["mean_error"])))

    if not grouped:
        raise SystemExit("summary CSV contains no rows")

    _, ax = plt.subplots(figsize=(11, 5.5))
    for method, points in sorted(grouped.items()):
        points.sort()
        xs = [point[0] for point in points]
        ys = [max(point[1], 1e-16) for point in points]
        ax.plot(xs, ys, marker="o", markersize=3, label=method.upper())

    ax.set_yscale("log")
    ax.set_xlabel("CEC2017 function")
    ax.set_ylabel("Mean objective error")
    ax.set_title("BoundEvo CEC2017 comparison")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend()
    ax.figure.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ax.figure.savefig(args.output, dpi=180)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
