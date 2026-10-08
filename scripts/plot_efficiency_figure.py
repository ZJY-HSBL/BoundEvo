"""Plot the M-versus-efficiency relationship for RE, EDBF, and ABC."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from boundevo.sweep import METHOD_LABELS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=Path("results/coefficient_efficiency.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/coefficient_efficiency.png"),
    )
    args = parser.parse_args()

    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        raise SystemExit('plotting requires: pip install -e ".[plot]"') from exc

    grouped: dict[str, list[tuple[int, float]]] = defaultdict(list)
    with args.input.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped[row["method"]].append(
                (int(row["parent_count"]), float(row["efficiency"]))
            )
    if not grouped:
        raise SystemExit("efficiency CSV contains no rows")

    _, ax = plt.subplots(figsize=(7.2, 4.8))
    for method, points in sorted(grouped.items()):
        points.sort()
        ax.plot(
            [point[0] for point in points],
            [point[1] for point in points],
            marker="o",
            markersize=3,
            label=METHOD_LABELS.get(method, method),
        )
    ax.set_xlabel("Number of parents M")
    ax.set_ylabel("Coefficient-vector generation efficiency")
    ax.set_title("Coefficient generation efficiency vs multi-parent scale")
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend()
    ax.figure.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ax.figure.savefig(args.output, dpi=180)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
