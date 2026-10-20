"""Fresh-seed CEC2017 cross-function replication at 10k function evaluations.

This separate exploratory cohort must never be pooled with older seed sets.
Runs the same fixed paper-style optimizer with matched initial populations.
"""

from __future__ import annotations

from itertools import pairwise

import argparse
import csv
import json
import math
import os
from dataclasses import asdict, fields
from pathlib import Path

from boundevo.cec2017 import REFERENCE_COMMIT, make_cec2017_case
from boundevo.experiments import HistoryRecord, TrialRecord, paper_config, run_case

FUNCTIONS = (3, 10, 20, 30)
METHODS = ("abc", "edbf", "re")
REPEATS = 10
BASE_SEED = 20261079
BUDGET = 10_000
INTERVAL = 450


def run(fid: int, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {
        "function_id": fid, "dimension": 30, "methods": list(METHODS),
        "repeats": REPEATS, "base_seed": BASE_SEED,
        "evaluations": BUDGET, "history_interval": INTERVAL,
        "reference_commit": REFERENCE_COMMIT, "source_commit": os.getenv("GITHUB_SHA"),
        "independent_of": "cec2017-holdout-30d-10k-2026-10-17",
        "cohort_design": "fresh random seeds; functions chosen after older suite inspection",
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    columns = [f.name for f in fields(TrialRecord)]
    hist_columns = [f.name for f in fields(HistoryRecord)]
    case = make_cec2017_case(fid, 30, backend="reference")
    with ((destination / "trials.csv").open("w", newline="", encoding="utf-8") as output,
          (destination / "history.csv").open("w", newline="", encoding="utf-8") as hist):
        writer = csv.DictWriter(output, fieldnames=columns)
        hwriter = csv.DictWriter(hist, fieldnames=hist_columns)
        writer.writeheader()
        hwriter.writeheader()
        for rep in range(REPEATS):
            seed = BASE_SEED + fid * 10000 + rep
            initial_best = None
            for method in METHODS:
                states: list[HistoryRecord] = []
                row = run_case(
                    case, method=method, repeat=rep, seed=seed,
                    config=paper_config(method=method, seed=seed, max_evaluations=BUDGET),
                    history_records=states, history_interval=INTERVAL,
                )
                if row.evaluations != BUDGET or not math.isfinite(row.error):
                    raise RuntimeError("actual run failed fixed 10k budget / finiteness gate")
                if not states or states[0].evaluations != 100 or states[-1].evaluations != BUDGET:
                    raise RuntimeError("incomplete initialization/final convergence evidence")
                if initial_best is not None and not math.isclose(
                    initial_best, states[0].best_error, rel_tol=1e-12, abs_tol=1e-9
                ):
                    raise RuntimeError("paired methods did not start from identical population")
                initial_best = states[0].best_error
                if not math.isclose(states[-1].best_error, row.error, rel_tol=1e-9, abs_tol=1e-7):
                    raise RuntimeError("final history and trial records disagree")
                if any(
                    b.best_error > a.best_error + 1e-7
                    for a, b in pairwise(states)
                ):
                    raise RuntimeError("best-so-far trace regressed")
                writer.writerow(asdict(row))
                hwriter.writerows(asdict(s) for s in states)
                output.flush()
                hist.flush()
                print(
                    f"F{fid} repeat={rep} {method} seed={seed} "
                    f"error={row.error:.8g} elapsed={row.elapsed_seconds:.2f}s",
                    flush=True,
                )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--function-id", type=int, choices=FUNCTIONS, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    run(args.function_id, args.output_dir)


if __name__ == "__main__":
    main()
