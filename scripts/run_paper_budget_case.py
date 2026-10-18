"""Run CEC2017 F16/F22 at the source paper's 100,000 evaluation cap.

Each trial is checked against its own *previously measured* 10k-FE prefix.
The current study samples the first five paired seeds from the independent
20-seed holdout; those five seeds are not new independent observations.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from dataclasses import asdict, fields
from pathlib import Path

from boundevo.cec2017 import REFERENCE_COMMIT, make_cec2017_case
from boundevo.experiments import HistoryRecord, TrialRecord, paper_config, run_case

METHODS = ("abc", "edbf", "re")
BASE_SEED = 20261037
HISTORY_INTERVAL = 900
BUDGET = 100_000
REPEATS = 5


def baseline_holdout(path: Path, fid: int) -> dict[tuple[int, str], float]:
    if not path.is_file():
        raise ValueError(f"missing committed 10k-FE baseline: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))
    if len(records) != 120:
        raise ValueError("the prior 20-seed experiment must contain 120 trials")
    selected = {}
    for row in records:
        function_id = int(row["function_id"])
        repeat = int(row["repeat"])
        method = row["method"]
        if function_id == fid and 0 <= repeat < REPEATS:
            if method not in METHODS or (repeat, method) in selected:
                raise ValueError("duplicate or invalid prior trial")
            if (
                int(row["evaluations"]) != 10000
                or int(row["seed"]) != BASE_SEED + fid * 10000 + repeat
            ):
                raise ValueError("prior cohort uses mismatched seeds or FE budget")
            value = float(row["error"])
            if not math.isfinite(value) or value < 0:
                raise ValueError("prior experiment has an invalid objective gap")
            selected[(repeat, method)] = value
    if set(selected) != {(repeat, method) for repeat in range(REPEATS) for method in METHODS}:
        raise ValueError("prior F16/F22 holdout is incomplete")
    return selected


def select_prefix(records: list[HistoryRecord], fid: int, method: str) -> float:
    at_ten_k = [state for state in records if state.evaluations == 10_000]
    if len(at_ten_k) != 1:
        raise RuntimeError(f"F{fid} {method}: required 10k checkpoint missing")
    return at_ten_k[0].best_error


def prefix_verified(prior: float, observed: float) -> bool:
    if not math.isfinite(prior) or not math.isfinite(observed):
        return False
    return math.isclose(prior, observed, rel_tol=1e-9, abs_tol=1e-6)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--function-id", type=int, choices=(16, 22), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--prior-trials",
        type=Path,
        default=Path(
            "docs/experiments/cec2017-holdout-30d-10k-2026-10-17/trials.csv"
        ),
    )
    args = parser.parse_args()
    fid = args.function_id
    initial = baseline_holdout(args.prior_trials, fid)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "function_id": fid,
        "dimension": 30,
        "methods": list(METHODS),
        "repeats": REPEATS,
        "evaluations": BUDGET,
        "baseline_evaluations": 10000,
        "base_seed": BASE_SEED,
        "reference_commit": REFERENCE_COMMIT,
        "history_interval": HISTORY_INTERVAL,
        "git_sha": os.getenv("GITHUB_SHA"),
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    trial_columns = [
        field.name for field in fields(TrialRecord)
    ] + ["baseline_10k_error", "measured_10k_error", "meanwhile_improvement"]
    history_columns = [field.name for field in fields(HistoryRecord)]
    with (
        (out / "trials.csv").open("w", newline="", encoding="utf-8") as trial_file,
        (out / "history.csv").open("w", newline="", encoding="utf-8") as hist_file,
    ):
        writer = csv.DictWriter(trial_file, fieldnames=trial_columns)
        history_writer = csv.DictWriter(hist_file, fieldnames=history_columns)
        writer.writeheader()
        history_writer.writeheader()
        case = make_cec2017_case(fid, 30, backend="reference")
        for repeat in range(REPEATS):
            seed = BASE_SEED + fid * 10000 + repeat
            for method in METHODS:
                states: list[HistoryRecord] = []
                result = run_case(
                    case,
                    method=method,
                    repeat=repeat,
                    seed=seed,
                    config=paper_config(
                        method=method, seed=seed, max_evaluations=BUDGET
                    ),
                    history_records=states,
                    history_interval=HISTORY_INTERVAL,
                )
                if result.evaluations != BUDGET:
                    raise RuntimeError(
                        f"F{fid} rep={repeat} {method} stopped at "
                        f"{result.evaluations}, expected {BUDGET}"
                    )
                if (
                    not states or states[0].evaluations != 100
                    or states[-1].evaluations != BUDGET
                ):
                    raise RuntimeError("missing initial or final checkpoint")
                prior = initial[(repeat, method)]
                current = select_prefix(states, fid, method)
                if not prefix_verified(prior, current):
                    raise RuntimeError(
                        f"10k-prefix mismatch for F{fid} rep={repeat} "
                        f"{method}: prior={prior}, 100k-run={current}"
                    )
                if result.error > current + 1e-7:
                    raise RuntimeError("best error increased over 100k evaluations")
                data = asdict(result)
                data["baseline_10k_error"] = prior
                data["measured_10k_error"] = current
                data["meanwhile_improvement"] = prior - result.error
                writer.writerow(data)
                history_writer.writerows(asdict(state) for state in states)
                trial_file.flush()
                hist_file.flush()
                print(
                    f"F{fid} repeat={repeat} {method} "
                    f"error10k={prior:.7g} error100k={result.error:.7g} "
                    f"improvement={prior - result.error:.7g} "
                    f"elapsed={result.elapsed_seconds:.2f}s",
                    flush=True,
                )


if __name__ == "__main__":
    main()
