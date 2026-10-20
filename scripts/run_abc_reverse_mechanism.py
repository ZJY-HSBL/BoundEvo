"""Three-way rank-order mechanism study: ABC, shuffle and zero-extra-RNG reverse."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from dataclasses import asdict, fields
from itertools import pairwise
from pathlib import Path

from boundevo.cec2017 import REFERENCE_COMMIT, make_cec2017_case
from boundevo.experiments import HistoryRecord, TrialRecord, paper_config, run_case

FUNCTIONS = (10, 16, 20, 22)
METHODS = ("abc", "abc_shuffle", "abc_reverse")
SEED_BASE = 20261231
REPEATS = 12
BUDGET = 10_000
INTERVAL = 450


def run(fid: int, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "function_id": fid, "methods": list(METHODS), "dimension": 30,
        "repeats": REPEATS, "evaluations": BUDGET, "base_seed": SEED_BASE,
        "history_interval": INTERVAL, "reference_commit": REFERENCE_COMMIT,
        "source_commit": os.environ.get("GITHUB_SHA"),
        "ablation": "ABC vs shuffle vs reversal of identical ABC coefficient multiset",
        "interpretation": "frozen exploratory rank-position controls: reversal uses no extra RNG",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2)+"\n", encoding="utf-8"
    )
    case = make_cec2017_case(fid, 30, backend="reference")
    with ((output / "trials.csv").open("w", newline="", encoding="utf-8") as trial_file,
          (output / "history.csv").open("w", newline="", encoding="utf-8") as hist_file):
        trial_writer = csv.DictWriter(trial_file, fieldnames=[f.name for f in fields(TrialRecord)])
        hist_writer = csv.DictWriter(hist_file, fieldnames=[f.name for f in fields(HistoryRecord)])
        trial_writer.writeheader()
        hist_writer.writeheader()
        for repeat in range(REPEATS):
            seed = SEED_BASE + fid*10000 + repeat
            initial = None
            for method in METHODS:
                states: list[HistoryRecord] = []
                result = run_case(
                    case, method=method, repeat=repeat, seed=seed,
                    config=paper_config(
                        method=method, seed=seed, max_evaluations=BUDGET
                    ), history_records=states, history_interval=INTERVAL,
                )
                if result.evaluations != BUDGET or not math.isfinite(result.error):
                    raise ValueError("trial failed fixed evaluation budget or produced nonfinite result")
                if not states or states[0].evaluations != 100 or states[-1].evaluations != BUDGET:
                    raise ValueError("missing real initial or final checkpoint")
                if initial is not None and not math.isclose(
                    initial, states[0].best_error, rel_tol=1e-12, abs_tol=1e-8
                ):
                    raise ValueError("coefficient-order controls did not start from identical parents")
                initial = states[0].best_error
                if any(b.best_error > a.best_error+1e-7 for a, b in pairwise(states)):
                    raise ValueError("nonmonotonic optimizer history")
                if not math.isclose(result.error, states[-1].best_error, abs_tol=1e-6):
                    raise ValueError("trial and history final errors differ")
                trial_writer.writerow(asdict(result))
                hist_writer.writerows(asdict(state) for state in states)
                trial_file.flush()
                hist_file.flush()
                print(
                    f"F{fid} repeat={repeat} method={method} error={result.error:.8g} "
                    f"elapsed={result.elapsed_seconds:.2f}s", flush=True
                )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--function-id", required=True, type=int, choices=FUNCTIONS)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    run(args.function_id, args.output_dir)


if __name__ == "__main__":
    main()
