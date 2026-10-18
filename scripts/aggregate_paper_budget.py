"""Validate 100k-FE trajectories, strictly paired with published 10k-FE data.

Statistics are descriptive: only five paired seeds per function are tested.
Each reported 10k checkpoint must reproduce the already published 20-seed
holdout's first five seeds, not merely match an invented synthetic baseline.
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
from pathlib import Path

from boundevo.cec2017 import REFERENCE_COMMIT

FUNCTIONS = (16, 22)
METHODS = ("abc", "edbf", "re")
REPEATS = 5
BUDGET = 100_000
BASE_SEED = 20261037


def read(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError(f"missing benchmark artifact {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write(path: Path, records: list[dict]) -> None:
    if not records:
        raise ValueError("cannot write an empty benchmark file")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def validate(source: Path) -> tuple[list[dict], list[dict], list[dict]]:
    trials, history, manifests = [], [], []
    for fid in FUNCTIONS:
        folder = source / f"f{fid}"
        manifest_file = folder / "manifest.json"
        if not manifest_file.is_file():
            raise ValueError(f"missing F{fid} manifest")
        env = json.loads(manifest_file.read_text(encoding="utf-8"))
        expected = {
            "function_id": fid, "dimension": 30, "methods": list(METHODS),
            "repeats": REPEATS, "evaluations": BUDGET,
            "baseline_evaluations": 10000, "base_seed": BASE_SEED,
            "reference_commit": REFERENCE_COMMIT, "history_interval": 900,
        }
        if any(env.get(name) != value for name, value in expected.items()):
            raise ValueError(f"F{fid} manifest protocol mismatch")
        part_trials = read(folder / "trials.csv")
        part_history = read(folder / "history.csv")
        if len(part_trials) != REPEATS * len(METHODS):
            raise ValueError(f"missing 100k F{fid} trials")
        trials.extend(part_trials)
        history.extend(part_history)
        manifests.append(env)
    expected_keys = {
        (fid, rep, method)
        for fid in FUNCTIONS for rep in range(REPEATS) for method in METHODS
    }
    observed = {}
    for row in trials:
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key not in expected_keys or key in observed:
            raise ValueError(f"unexpected or duplicate experiment trial {key}")
        fid, rep, _ = key
        if (
            int(row["seed"]) != BASE_SEED + fid * 10000 + rep
            or int(row["dimension"]) != 30
            or int(row["evaluations"]) != BUDGET
        ):
            raise ValueError(f"invalid paired seed or evaluation budget: {key}")
        for column in (
            "objective", "optimum", "error", "elapsed_seconds",
            "baseline_10k_error", "measured_10k_error", "meanwhile_improvement",
        ):
            if not math.isfinite(float(row[column])):
                raise ValueError(f"nonfinite {column} at {key}")
        gap = float(row["objective"]) - float(row["optimum"])
        if (
            gap < -1e-7
            or not math.isclose(float(row["error"]), gap, abs_tol=1e-6)
            or not math.isclose(
                float(row["baseline_10k_error"]),
                float(row["measured_10k_error"]),
                rel_tol=1e-9, abs_tol=1e-6,
            )
            or not math.isclose(
                float(row["meanwhile_improvement"]),
                float(row["baseline_10k_error"]) - float(row["error"]),
                abs_tol=1e-6,
            )
            or float(row["meanwhile_improvement"]) < -1e-7
        ):
            raise ValueError(f"invalid numerical budget progression: {key}")
        observed[key] = row
    if set(observed) != expected_keys:
        raise ValueError("30-trial budget comparison is incomplete")

    states = defaultdict(list)
    for row in history:
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key not in expected_keys:
            raise ValueError(f"unexpected history trial {key}")
        if int(row["dimension"]) != 30:
            raise ValueError("convergence history dimension mismatch")
        fe = int(row["evaluations"])
        if not 100 <= fe <= BUDGET:
            raise ValueError("history function evaluation out of range")
        if not math.isfinite(float(row["best_error"])):
            raise ValueError("nonfinite history objective")
        states[key].append(row)
    if set(states) != expected_keys:
        raise ValueError("convergence history missing a trial")
    for key, checkpoints in states.items():
        ordered = sorted(checkpoints, key=lambda row: int(row["evaluations"]))
        budget_points = [int(row["evaluations"]) for row in ordered]
        if (
            budget_points[0] != 100 or budget_points[-1] != BUDGET
            or budget_points != sorted(set(budget_points))
            or budget_points.count(10000) != 1
        ):
            raise ValueError(f"missing or duplicated budget checkpoints: {key}")
        objectives = [float(row["best_error"]) for row in ordered]
        if any(curr > prev + 1e-7 for prev, curr in zip(objectives, objectives[1:])):
            raise ValueError(f"best-so-far objective became worse: {key}")
        prefix = next(
            float(row["best_error"]) for row in ordered
            if int(row["evaluations"]) == 10000
        )
        final = objectives[-1]
        original = observed[key]
        if (
            not math.isclose(
                prefix, float(original["baseline_10k_error"]),
                rel_tol=1e-9, abs_tol=1e-6,
            )
            or not math.isclose(
                final, float(original["error"]), rel_tol=1e-9, abs_tol=1e-6
            )
        ):
            raise ValueError(f"recorded trajectory does not match raw trial: {key}")
    return trials, history, manifests


def summary(trials: list[dict]) -> list[dict]:
    by_group = defaultdict(list)
    for trial in trials:
        by_group[(int(trial["function_id"]), trial["method"])].append(trial)
    output = []
    for (fid, method), items in sorted(by_group.items()):
        if len(items) != REPEATS:
            raise ValueError("incomplete summary")
        initial = [float(row["baseline_10k_error"]) for row in items]
        final = [float(row["error"]) for row in items]
        mean_initial = statistics.fmean(initial)
        mean_final = statistics.fmean(final)
        output.append(
            {
                "function_id": fid, "method": method, "repeats": REPEATS,
                "mean_error_10k": mean_initial,
                "mean_error_100k": mean_final,
                "std_error_100k": statistics.stdev(final),
                "mean_improvement": mean_initial - mean_final,
                "relative_improvement_pct": (
                    100 * (1 - mean_final / mean_initial)
                    if mean_initial > 0 else float("nan")
                ),
                "mean_elapsed_seconds": statistics.fmean(
                    float(row["elapsed_seconds"]) for row in items
                ),
                "mean_evaluations": BUDGET,
            }
        )
    return output


def report(summary_rows: list[dict], trials: list[dict]) -> str:
    lookup = {
        (int(row["function_id"]), row["method"]): row
        for row in summary_rows
    }
    lines = [
        "# CEC2017 F16/F22: paired 10k-to-100k evaluation budget study",
        "",
        "30 completed trials (2 functions × 3 coefficient generators × 5 seeds), "
        "D=30, capped at 100,000 function evaluations per trial. "
        "The same five seeds are a subset of the earlier **20-seed** "
        "10,000-evaluation holdout (not 5 fresh additional seeds).",
        "",
        "The prior observed 10k errors are verified against exact FE=10000 "
        "checkpoints inside each continuing 100k optimization trajectory.",
        "",
        "| Function | Method | 10k mean error | 100k mean error | Improvement |",
        "|:---|:---|---:|---:|---:|",
    ]
    for fid in FUNCTIONS:
        for method in METHODS:
            row = lookup[(fid, method)]
            lines.append(
                f"| F{fid} | {method.upper()} | {row['mean_error_10k']:.6g} | "
                f"{row['mean_error_100k']:.6g} | "
                f"{row['relative_improvement_pct']:+.2f}% |"
            )
    lines += [
        "",
        "## Interpretation limits",
        "",
        "- Five matched seeds per function provide exploratory convergence "
        "trajectories, not robust statistical evidence of superiority.",
        "- 100,000 evaluations match the source-paper upper budget but only "
        "two of 29 official CEC2017 functions are included.",
        "- These runs use the pinned independent Python CEC2017 reference "
        "port; it is not the original organizers' C benchmark binary.",
        "- Because these seeds were used in the previous 10k holdout, "
        "do not call them an independent 5-seed validation cohort.",
        "- A best-so-far objective cannot worsen with a higher evaluation "
        "budget for the **same deterministic run**; the scientific question "
        "is how the *relative efficiency and convergence rates* change.",
        "",
        "## Source evidence",
        "",
        "[30 original trials](trials.csv) · [sampled convergence curves](history.csv) · "
        "[per-method means](summary.csv) · [run manifests](environment.json)",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    trials, history, manifests = validate(args.input_dir)
    result = summary(trials)
    target = args.output_dir
    target.mkdir(parents=True, exist_ok=True)
    trials.sort(key=lambda x: (int(x["function_id"]), int(x["repeat"]), x["method"]))
    history.sort(
        key=lambda x: (
            int(x["function_id"]), int(x["repeat"]), x["method"],
            int(x["evaluations"]),
        )
    )
    write(target / "trials.csv", trials)
    write(target / "history.csv", history)
    write(target / "summary.csv", result)
    config = {
        "functions": list(FUNCTIONS),
        "methods": list(METHODS),
        "dimension": 30,
        "repeats": REPEATS,
        "evaluations": BUDGET,
        "baseline_evaluations": 10000,
        "base_seed": BASE_SEED,
        "source_holdout_seed_subset": list(range(REPEATS)),
        "reference_commit": REFERENCE_COMMIT,
        "trials": len(trials),
        "history_rows": len(history),
        "source_git_shas": [x.get("git_sha") for x in manifests],
        "python": sys.version,
        "platform": platform.platform(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    (target / "environment.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
    (target / "report.md").write_text(report(result, trials), encoding="utf-8")
    print(
        f"Validated {len(trials)} complete 100k-FE trials, "
        f"{len(history)} convergence checkpoints.",
        flush=True,
    )


if __name__ == "__main__":
    main()
