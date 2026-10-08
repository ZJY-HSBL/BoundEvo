"""Plot objective error, runtime, and evaluations for the parent-count sweep."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from boundevo.sweep import METHOD_LABELS


def _load(path: Path) -> dict[int, list[dict[str, str]]]:
    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped[int(row["function_id"])].append(row)
    return grouped


def _plot_metric(
    rows: list[dict[str, str]],
    *,
    function_id: int,
    metric: str,
    ylabel: str,
    output: Path,
    log_scale: bool = False,
) -> None:
    import matplotlib.pyplot as plt

    by_method: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for row in rows:
        value = float(row[metric])
        if log_scale:
            value = max(value, 1e-16)
        by_method[row["method"]].append((int(row["parent_count"]), value))

    _, ax = plt.subplots(figsize=(7.2, 4.8))
    for method, points in sorted(by_method.items()):
        points.sort()
        ax.plot(
            [point[0] for point in points],
            [point[1] for point in points],
            marker="o",
            label=METHOD_LABELS.get(method, method),
        )
    if log_scale:
        ax.set_yscale("log")
    ax.set_xlabel("Number of parents M")
    ax.set_ylabel(ylabel)
    ax.set_title(f"CEC2017 F{function_id}: {ylabel} vs M")
    ax.grid(True, alpha=0.25)
    ax.legend()
    ax.figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    ax.figure.savefig(output, dpi=180)
    plt.close(ax.figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "summary",
        type=Path,
        nargs="?",
        default=Path("results/parent_sweep_summary.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/parent_sweep_figures"),
    )
    args = parser.parse_args()

    try:
        import matplotlib.pyplot as plt  # noqa: F401
    except ModuleNotFoundError as exc:
        raise SystemExit('plotting requires: pip install -e ".[plot]"') from exc

    grouped = _load(args.summary)
    if not grouped:
        raise SystemExit("summary CSV contains no rows")

    for function_id, rows in sorted(grouped.items()):
        _plot_metric(
            rows,
            function_id=function_id,
            metric="best_error",
            ylabel="Best objective error",
            output=args.output_dir / f"F{function_id}_error.png",
            log_scale=True,
        )
        _plot_metric(
            rows,
            function_id=function_id,
            metric="mean_elapsed_seconds",
            ylabel="Mean runtime (s)",
            output=args.output_dir / f"F{function_id}_runtime.png",
        )
        _plot_metric(
            rows,
            function_id=function_id,
            metric="mean_evaluations",
            ylabel="Mean function evaluations",
            output=args.output_dir / f"F{function_id}_evaluations.png",
        )
    print(f"wrote figures to {args.output_dir}")


if __name__ == "__main__":
    main()
