"""Validate and aggregate four independently completed CEC2017 experiment shards.

Reject missing trials, duplicates, unpaired initial seeds, invalid checkpoints,
backend mismatches, and nonfinite errors. Report only fully verified cohorts.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np

from boundevo.cec2017 import PAPER_FUNCTION_IDS, REFERENCE_COMMIT

METHODS = ("abc", "edbf", "re")


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"missing shard CSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def aggregate(source: Path, shard_count: int, repeats: int, evaluations: int):
    if shard_count < 1 or repeats < 1 or evaluations < 100:
        raise ValueError("invalid shard count, repeats, or budget")
    ids = set(PAPER_FUNCTION_IDS)
    all_trials: list[dict] = []
    all_history: list[dict] = []
    observed_functions: set[int] = set()
    manifests = []
    for index in range(shard_count):
        folder = source / f"shard-{index}"
        manifest = json.loads((folder / "shard_manifest.json").read_text(encoding="utf-8"))
        expected = PAPER_FUNCTION_IDS[index::shard_count]
        if (
            manifest["index"] != index
            or manifest["count"] != shard_count
            or tuple(manifest["function_ids"]) != expected
            or manifest["methods"] != list(METHODS)
            or manifest["reference_commit"] != REFERENCE_COMMIT
            or manifest["dimension"] != 30
            or manifest["evaluations"] != evaluations
            or manifest["repeats"] != repeats
            or manifest["history_interval"] != 500
            or manifest["base_seed"] != 20261017
        ):
            raise ValueError(f"inconsistent experiment protocol in shard {index}")
        if observed_functions.intersection(expected):
            raise ValueError("function was assigned to multiple shards")
        observed_functions.update(expected)
        manifests.append(manifest)
        trials = load_csv(folder / "trials.csv")
        history = load_csv(folder / "history.csv")
        if len(trials) != len(expected) * repeats * len(METHODS):
            raise ValueError(f"shard {index} has incomplete trial coverage")
        all_trials.extend(trials)
        all_history.extend(history)
    if observed_functions != ids:
        raise ValueError("full CEC2017 function set is incomplete")
    if len(all_trials) != 29 * repeats * len(METHODS):
        raise ValueError("unexpected full-suite trial count")

    trial_groups = defaultdict(list)
    trial_keys = set()
    for row in all_trials:
        fid, rep, method = int(row["function_id"]), int(row["repeat"]), row["method"]
        key = (fid, rep, method)
        if key in trial_keys or fid not in ids or not 0 <= rep < repeats or method not in METHODS:
            raise ValueError(f"duplicate or unexpected trial {key}")
        trial_keys.add(key)
        if int(row["dimension"]) != 30 or int(row["evaluations"]) != evaluations:
            raise ValueError(f"invalid trial dimension or evaluation budget: {key}")
        if int(row["seed"]) != 20261017 + fid * 10000 + rep:
            raise ValueError(f"unexpected matched initial seed {key}")
        gap = float(row["objective"]) - float(row["optimum"])
        for field in ("objective", "optimum", "error", "elapsed_seconds", "attempts_per_offspring"):
            if not math.isfinite(float(row[field])):
                raise ValueError(f"nonfinite {field} in {key}")
        if gap < -1e-7 or not math.isclose(float(row["error"]), max(0.0, gap), abs_tol=1e-6):
            raise ValueError(f"benchmark error differs from known optimum: {key}")
        if float(row["attempts_per_offspring"]) < 1:
            raise ValueError(f"invalid coefficient attempts in {key}")
        trial_groups[(fid, rep)].append(row)
    if len(trial_groups) != 29 * repeats:
        raise ValueError("missing function/repetition pairs")
    for key, rows in trial_groups.items():
        if len(rows) != 3 or {row["method"] for row in rows} != set(METHODS):
            raise ValueError(f"incomplete method pairing for {key}")

    hist_groups = defaultdict(list)
    for row in all_history:
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key not in trial_keys:
            raise ValueError(f"history has unknown trial key {key}")
        if int(row["dimension"]) != 30:
            raise ValueError("history has unexpected dimension")
        for field in ("best_error", "best_objective", "worst_objective"):
            if not math.isfinite(float(row[field])):
                raise ValueError(f"nonfinite history {field} at {key}")
        hist_groups[key].append(row)
    if set(hist_groups) != trial_keys:
        raise ValueError("missing convergence history for some trials")
    lookup = {(int(r["function_id"]), int(r["repeat"]), r["method"]): r for r in all_trials}
    for key, rows in hist_groups.items():
        rows.sort(key=lambda row: int(row["evaluations"]))
        steps = [int(row["evaluations"]) for row in rows]
        if (
            steps[0] != 100
            or steps[-1] != evaluations
            or steps != sorted(set(steps))
            or any(step < 100 or step > evaluations for step in steps)
        ):
            raise ValueError(f"missing/invalid initial or final convergence snapshots: {key}")
        objectives = [float(row["best_objective"]) for row in rows]
        tolerance = 1e-7
        if any(later > earlier + tolerance for earlier, later in zip(objectives, objectives[1:])):
            raise ValueError(f"best objective worsened in convergence history: {key}")
        if not math.isclose(objectives[-1], float(lookup[key]["objective"]), rel_tol=1e-10):
            raise ValueError(f"history final value mismatches trial summary: {key}")

    return all_trials, all_history, manifests


def summaries(trials: list[dict], repeats: int) -> list[dict]:
    by_case = defaultdict(list)
    for row in trials:
        by_case[(int(row["function_id"]), row["method"])].append(row)
    result = []
    for (fid, method), rows in sorted(by_case.items()):
        if len(rows) != repeats:
            raise ValueError("incomplete summary cohort")
        errors = [float(row["error"]) for row in rows]
        runtimes = [float(row["elapsed_seconds"]) for row in rows]
        attempts = [float(row["attempts_per_offspring"]) for row in rows]
        result.append(
            {
                "function_id": fid,
                "method": method,
                "repeats": repeats,
                "mean_error": statistics.fmean(errors),
                "std_error": statistics.stdev(errors) if repeats > 1 else 0,
                "median_error": statistics.median(errors),
                "mean_elapsed_seconds": statistics.fmean(runtimes),
                "mean_evaluations": statistics.fmean(float(r["evaluations"]) for r in rows),
                "mean_attempts_per_offspring": statistics.fmean(attempts),
            }
        )
    return result


def compare_function_ranks(summary: list[dict]):
    from scipy.stats import friedmanchisquare, wilcoxon

    by_case = {(int(r["function_id"]), r["method"]): float(r["mean_error"]) for r in summary}
    winners = {method: 0 for method in METHODS}
    ranks = {method: 0.0 for method in METHODS}
    function_results = []
    for fid in PAPER_FUNCTION_IDS:
        values = {m: by_case[(fid, m)] for m in METHODS}
        leader = min(METHODS, key=lambda m: values[m])
        winners[leader] += 1
        ordered = sorted(METHODS, key=lambda m: values[m])
        for rank, method in enumerate(ordered, start=1):
            ranks[method] += rank
        function_results.append(
            {"function_id": fid, **{m + "_mean_error": values[m] for m in METHODS}, "leader": leader}
        )
    avg_ranks = {method: ranks[method] / len(PAPER_FUNCTION_IDS) for method in METHODS}
    arrays = [[by_case[(fid, method)] for fid in PAPER_FUNCTION_IDS] for method in METHODS]
    chi_square, friedman_p = friedmanchisquare(*arrays)
    contrasts = []
    for method in ("edbf", "re"):
        differences = np.array(
            [
                math.log10(max(by_case[(fid, method)], 1e-12))
                - math.log10(max(by_case[(fid, "abc")], 1e-12))
                for fid in PAPER_FUNCTION_IDS
            ]
        )
        stat, p = wilcoxon(differences, zero_method="wilcox", alternative="two-sided")
        contrasts.append(
            {
                "comparison": "abc_vs_" + method,
                "wilcoxon_statistic": float(stat),
                "raw_p": float(p),
                "wins": int(sum(x > 0 for x in differences)),
                "losses": int(sum(x < 0 for x in differences)),
            }
        )
    # Holm step-down procedure across the two prespecified algorithm contrasts.
    ordered = sorted(contrasts, key=lambda row: row["raw_p"])
    previous = 0.0
    for i, row in enumerate(ordered):
        previous = max(previous, min(1.0, row["raw_p"] * (len(ordered) - i)))
        row["holm_p"] = previous
    return function_results, winners, avg_ranks, float(chi_square), float(friedman_p), contrasts


def report(
    environment: dict, function_results: list[dict], leaders: dict,
    avg_ranks: dict, friedman: tuple[float, float], contrasts: list[dict],
) -> str:
    lines = [
        "# Full-suite CEC2017 30D: 10,000-FE exploratory study",
        "",
        "## Protocol",
        "",
        "- 29 official CEC2017 functions (F1 and F3–F30), 30 dimensions.",
        "- ABC, EDBF, RE; three independent paired initial seeds per function.",
        "- 10,000 objective evaluations per trial, including 100 initialization.",
        "- Fixed N=100, M=15, K=5, L=1, history sampled every 500 generations.",
        "- Independent reference-derived CEC2017 backend, pinned to " + REFERENCE_COMMIT + ".",
        f"- Completed **{environment['trials']} real trials**, strictly validated.",
        "",
        "## Observed function-level leaders and mean ranks",
        "",
        "| Method | Function-level mean leaders | Average rank (lower better) |",
        "|:---|---:|---:|",
    ]
    for method in METHODS:
        lines.append(f"| {method.upper()} | {leaders[method]} | {avg_ranks[method]:.3f} |")
    lines += [
        "",
        f"Friedman statistic: {friedman[0]:.6g}, asymptotic p={friedman[1]:.6g} "
        "(29 function-level matched groups).",
        "",
        "### Paired Wilcoxon on log10 function-level mean error",
        "",
        "| Contrast | ABC lower / higher | Unadjusted p | Holm-adjusted p |",
        "|:---|---:|---:|---:|",
    ]
    for row in contrasts:
        lines.append(
            f"| {row['comparison']} | {row['wins']} / {row['losses']} | "
            f"{row['raw_p']:.6g} | {row['holm_p']:.6g} |"
        )
    lines += [
        "",
        "## Detailed function results (mean objective error)",
        "",
        "| Function | ABC | EDBF | RE | Lowest observed mean |",
        "|:---|---:|---:|---:|:---|",
    ]
    for row in function_results:
        lines.append(
            f"| F{row['function_id']} | {row['abc_mean_error']:.6g} | "
            f"{row['edbf_mean_error']:.6g} | {row['re_mean_error']:.6g} | "
            f"{row['leader'].upper()} |"
        )
    lines += [
        "",
        "## Critical interpretation limits",
        "",
        "- Three repetitions per function provide limited within-function variance "
        "precision, and the function-level hypothesis tests should be exploratory.",
        "- The 29 benchmark functions share construction and are not 29 "
        "independent draws from all possible optimization problems.",
        "- An objective evaluation budget of 10,000 is not the 100,000-FE source "
        "paper budget; results cannot be cited as full source reproduction.",
        "- Comparisons of wall-clock time are runner- and Python-specific.",
        "- The pinned NumPy benchmark implementation derives from C but is not "
        "the organizers' official original C binary.",
        "- Do not pool this experiment with the earlier 1,200-FE or four-function "
        "3,000/10,000-FE cohorts.",
        "",
        "## Reproducibility",
        "",
        "All 261 trials and every convergence checkpoint are provided in the "
        "adjacent `trials.csv` and `history.csv`, with `summary.csv`, "
        "`function_ranks.csv` and `environment.json`.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--shards", type=int, default=4)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--evaluations", type=int, default=10000)
    args = parser.parse_args()
    trials, history, manifests = aggregate(args.input_dir, args.shards, args.repeats, args.evaluations)
    summary = summaries(trials, args.repeats)
    functions, leaders, ranks, statistic, p, contrasts = compare_function_ranks(summary)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    trials.sort(key=lambda row: (int(row["function_id"]), int(row["repeat"]), row["method"]))
    history.sort(
        key=lambda row: (
            int(row["function_id"]),
            int(row["repeat"]),
            row["method"],
            int(row["evaluations"]),
        )
    )
    write_csv(output / "trials.csv", trials)
    write_csv(output / "history.csv", history)
    write_csv(output / "summary.csv", summary)
    write_csv(output / "function_ranks.csv", functions)
    write_csv(output / "paired_function_tests.csv", contrasts)
    env = {
        "functions": list(PAPER_FUNCTION_IDS),
        "dimension": 30,
        "methods": list(METHODS),
        "repeats": args.repeats,
        "evaluations": args.evaluations,
        "history_interval": 500,
        "base_seed": 20261017,
        "reference_commit": REFERENCE_COMMIT,
        "shard_count": args.shards,
        "git_sha": os.getenv("GITHUB_SHA"),
        "trials": len(trials),
        "convergence_rows": len(history),
        "started_from_shard_commits": [part.get("git_sha") for part in manifests],
        "python": sys.version,
        "platform": platform.platform(),
        "numpy_version": np.__version__,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output / "environment.json").write_text(
        json.dumps(env, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "report.md").write_text(
        report(env, functions, leaders, ranks, (statistic, p), contrasts),
        encoding="utf-8",
    )
    print(
        f"Verified {len(trials)} full-suite trials and {len(history)} convergence states. "
        f"Observed mean-error leaders: {leaders}; Friedman p={p:.5g}",
        flush=True,
    )


if __name__ == "__main__":
    main()
