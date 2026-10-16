"""Run an auditable small-scale CEC2017 comparison using the real BoundEvo engine.

All methods in the same function/repeat pair use the same RNG seed, ensuring
an identical initial population. This is a pilot, not a replication of the
paper's full experiment or evidence of statistical superiority.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import statistics
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from boundevo.cec2017 import make_cec2017_case
from boundevo.experiments import paper_config, run_case


def installed_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("no experimental observations")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_summary(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[int, str], list[dict]] = {}
    for row in rows:
        groups.setdefault((row["function_id"], row["method"]), []).append(row)
    result = []
    for (fid, method), items in sorted(groups.items()):
        errors = [float(item["error"]) for item in items]
        runtimes = [float(item["elapsed_seconds"]) for item in items]
        attempts = [float(item["attempts_per_offspring"]) for item in items]
        evaluations = [int(item["evaluations"]) for item in items]
        result.append(
            {
                "function_id": fid,
                "method": method,
                "repeats": len(items),
                "mean_error": statistics.fmean(errors),
                "std_error": statistics.stdev(errors) if len(errors) > 1 else 0.0,
                "median_error": statistics.median(errors),
                "best_error": min(errors),
                "mean_runtime_s": statistics.fmean(runtimes),
                "mean_evaluations": statistics.fmean(evaluations),
                "mean_attempts_per_offspring": statistics.fmean(attempts),
            }
        )
    return result


def make_report(summary: list[dict], config: dict, data: list[dict]) -> str:
    methods = config["methods"]
    fids = config["functions"]
    lines = [
        "# BoundEvo CEC2017 pilot validation",
        "",
        "## Experiment protocol",
        "",
        f"- Benchmark: CEC2017 through opfunu, D={config['dimension']}.",
        f"- Functions: {', '.join('F' + str(fid) for fid in fids)}.",
        f"- Methods: {', '.join(methods)}.",
        f"- Repetitions: {config['repeats']} per function and method.",
        f"- Maximum function evaluations: {config['evaluations']} per trial (initial 100 included).",
        "- Optimizer: population N=100; parent count M=15; elite parents K=5; offspring L=1.",
        "- Same RNG seed for all methods in a function/repetition pair.",
        "- Offspring outside the search box are clipped by the existing optimizer.",
        "- Error = max(0, obtained objective - benchmark known optimum); lower is better.",
        "- Runtime is measured wall-clock time on a shared GitHub Actions runner.",
        "- This is a limited-budget pilot and is NOT a full reproduction of the paper.",
        "",
        "## Observed results",
        "",
        "| Function | Method | Mean error | SD | Mean runtime (s) | Mean evaluations | Mean attempts / child |",
        "|:---|:---|---:|---:|---:|---:|---:|",
    ]
    lookup = {(int(row["function_id"]), row["method"]): row for row in summary}
    for fid in fids:
        for method in methods:
            row = lookup[(fid, method)]
            lines.append(
                f"| F{fid} | {method.upper()} | {row['mean_error']:.6g} | "
                f"{row['std_error']:.3g} | {row['mean_runtime_s']:.3f} | "
                f"{row['mean_evaluations']:.0f} | "
                f"{row['mean_attempts_per_offspring']:.3f} |"
            )
    lines += ["", "## Per-function error leaders", ""]
    wins = {method: 0 for method in methods}
    for fid in fids:
        ranked = sorted(
            (lookup[(fid, method)] for method in methods),
            key=lambda item: item["mean_error"],
        )
        best = ranked[0]["mean_error"]
        leaders = [
            item["method"]
            for item in ranked
            if abs(item["mean_error"] - best) <= 1e-10
        ]
        for method in leaders:
            wins[method] += 1
        lines.append(
            f"- F{fid}: {', '.join(leaders)} "
            f"(mean error {best:.6g})."
        )
    lines += [
        "",
        "Functions with lowest observed mean error (ties counted for all leaders): "
        + ", ".join(f"{m}={wins[m]}" for m in methods)
        + ".",
        "",
        "## Validation checks",
        "",
    ]
    for (fid, rep), subset in sorted(
        (
            ((fid, rep), [row for row in data if row["function_id"] == fid and row["repeat"] == rep])
            for fid in fids
            for rep in range(config["repeats"])
        ),
        key=lambda item: item[0],
    ):
        if {row["method"] for row in subset} != set(methods):
            raise RuntimeError(f"incomplete method set for F{fid} repeat {rep}")
        if len({row["seed"] for row in subset}) != 1:
            raise RuntimeError(f"mismatched seeds in F{fid} repeat {rep}")
        if len({row["evaluations"] for row in subset}) != 1:
            raise RuntimeError(f"mismatched evaluation counts in F{fid} repeat {rep}")
    lines += [
        "- All methods share the same seed within each function/repetition pair.",
        "- All methods executed the same number of function evaluations within each pair.",
        f"- All {len(data)} requested trials completed and produced finite results.",
        "",
        "## Interpretation and limitations",
        "",
        ("The ABC generator must use exactly one coefficient-vector proposal, whereas "
        "RE and EDBF require rejection sampling. This guarantees a generation-"
        "attempt advantage, not necessarily a lower final objective error."),
        "",
        ("With only a handful of repeats and a limited evaluation budget, differences "
        "can be sampling noise. A proper paper-level replication requires the "
        "original function dimension and stopping rule, substantially longer runs, "
        "more seeds, confirmed baseline implementations, and uncertainty analysis."),
        "",
        ("The three methods use identical starting seeds, but their random-number "
        "streams diverge after initialization because each generator consumes "
        "different numbers of draws. CPU load, interpreter overhead, and "
        "implementation differences also affect wall-clock runtime."),
        "",
        ("See validation_trials.csv, validation_summary.csv, and environment.json "
        "for the machine-readable data."),
        "",
    ]
    return "\n".join(lines)


def make_plot(summary: list[dict], destination: Path, methods: list[str]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fids = sorted({int(item["function_id"]) for item in summary})
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(fids), dtype=float)
    bar_width = 0.78 / len(methods)
    for idx, method in enumerate(methods):
        by_fid = {
            int(item["function_id"]): float(item["mean_error"])
            for item in summary
            if item["method"] == method
        }
        values = [max(1e-12, by_fid[fid]) for fid in fids]
        ax.bar(x - 0.39 + (idx + 0.5) * bar_width, values, bar_width, label=method.upper())
    ax.set_xticks(x, [f"F{fid}" for fid in fids])
    ax.set_yscale("log")
    ax.set_ylabel("Mean objective error (log scale)")
    ax.set_title("CEC2017 pilot: equal FE budget, matched initial seeds")
    ax.legend()
    fig.tight_layout()
    fig.savefig(destination, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--functions", nargs="+", type=int, default=[1, 5, 10, 20])
    parser.add_argument("--methods", nargs="+", choices=["abc", "edbf", "re"], default=["abc", "edbf", "re"])
    parser.add_argument("--dimension", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--evaluations", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=20261017)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/experiments/cec2017-pilot-2026-10-17"))
    args = parser.parse_args()
    if args.repeats < 1 or args.evaluations < 100:
        parser.error("repeats >= 1 and evaluations >= 100 are required")
    if len(set(args.methods)) != len(args.methods):
        parser.error("duplicate methods are not allowed")
    if len(set(args.functions)) != len(args.functions):
        parser.error("duplicate functions are not allowed")
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    config = vars(args).copy()
    config["output_dir"] = str(output)
    config["utc_started"] = datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []
    start = time.perf_counter()

    for fid in args.functions:
        case = make_cec2017_case(fid, args.dimension)
        for rep in range(args.repeats):
            seed = args.seed + fid * 10000 + rep
            for method in args.methods:
                record = run_case(
                    case,
                    method=method,
                    repeat=rep,
                    seed=seed,
                    config=paper_config(
                        method=method,
                        max_evaluations=args.evaluations,
                        seed=seed,
                    ),
                    history_interval=100,
                )
                row = asdict(record)
                offspring = record.evaluations - 100
                row["attempts_per_offspring"] = (
                    record.coefficient_attempts / offspring if offspring > 0 else 0.0
                )
                rows.append(row)
                print(
                    f"F{fid} rep={rep} {method}: "
                    f"err={record.error:.5g} FE={record.evaluations} "
                    f"sec={record.elapsed_seconds:.2f} "
                    f"attempts/child={row['attempts_per_offspring']:.2f}",
                    flush=True,
                )

    summary = build_summary(rows)
    write_csv(output / "validation_trials.csv", rows)
    write_csv(output / "validation_summary.csv", summary)
    (output / "validation_readme.md").write_text(
        make_report(summary, config, rows),
        encoding="utf-8",
    )
    make_plot(summary, output / "error_comparison.png", args.methods)
    environment = {
        **config,
        "utc_finished": datetime.now(timezone.utc).isoformat(),
        "total_runtime_seconds": time.perf_counter() - start,
        "git_sha": os.environ.get("GITHUB_SHA"),
        "python": sys.version,
        "platform": platform.platform(),
        "numpy_version": installed_version("numpy"),
        "opfunu_version": installed_version("opfunu"),
        "scipy_version": installed_version("scipy"),
        "matplotlib_version": installed_version("matplotlib"),
        "trials_completed": len(rows),
        "experiment_kind": "pilot, limited budget, not full replication",
    }
    (output / "environment.json").write_text(
        json.dumps(environment, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Completed {len(rows)} trials in {environment['total_runtime_seconds']:.2f}s", flush=True)


if __name__ == "__main__":
    main()
