"""Execute the prespecified 29-function full-suite DE comparison, one shard/job.

Only genuine CEC2017 evaluations are written to evidence CSVs.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
from dataclasses import asdict, fields
from itertools import pairwise
from pathlib import Path

from boundevo.cec2017 import PAPER_FUNCTION_IDS, REFERENCE_COMMIT, make_cec2017_case
from boundevo.de_baseline import differential_evolution_rand1bin
from boundevo.experiments import (
    HistoryRecord,
    TrialRecord,
    paper_config,
    run_case,
)

# Frozen six-shard partition, covering all 29 official CEC2017 retained tasks.
SHARDS = (
    (1, 3, 4, 5, 6),
    (7, 8, 9, 10, 11),
    (12, 13, 14, 15, 16),
    (17, 18, 19, 20, 21),
    (22, 23, 24, 25, 26),
    (27, 28, 29, 30),
)
METHODS = ("abc", "abc_reverse", "de_rand1bin")
BASE_SEED = 20261021
REPEATS = 5
BUDGET = 10_000
HISTORY_INTERVAL = 100
DE_F = 0.8
DE_CR = 0.9


def validate_partition() -> None:
    flat = [fid for shard in SHARDS for fid in shard]
    if len(flat) != 29 or len(set(flat)) != 29 or set(flat) != set(PAPER_FUNCTION_IDS):
        raise ValueError("CEC2017 F1/F3–F30 partition is not exact")


def run(shard_id: int, destination: Path) -> None:
    validate_partition()
    tasks = SHARDS[shard_id]
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {
        "shard_id": shard_id, "functions": list(tasks),
        "official_function_ids": list(PAPER_FUNCTION_IDS),
        "methods": list(METHODS), "dimension": 30, "repeats": REPEATS,
        "base_seed": BASE_SEED, "evaluations": BUDGET,
        "history_interval": HISTORY_INTERVAL,
        "de_strategy": "generational DE/rand/1/bin, one-to-one greedy replacement",
        "de_population": 100, "de_mutation": DE_F, "de_crossover": DE_CR,
        "de_boundary": "clip", "de_preset": "fixed before data",
        "reference_commit": REFERENCE_COMMIT,
        "source_commit": os.environ.get("GITHUB_SHA"),
        "design": "full 29-function suite; new paired seeds; 5 repeats/function",
    }
    (destination/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    with ((destination/"trials.csv").open("w", newline="", encoding="utf-8") as tf,
          (destination/"history.csv").open("w", newline="", encoding="utf-8") as hf):
        trial_writer = csv.DictWriter(tf, fieldnames=[x.name for x in fields(TrialRecord)])
        hist_writer = csv.DictWriter(hf, fieldnames=[x.name for x in fields(HistoryRecord)])
        trial_writer.writeheader()
        hist_writer.writeheader()
        for fid in tasks:
            case = make_cec2017_case(fid, 30, backend="reference")
            for rep in range(REPEATS):
                seed = BASE_SEED + fid*10_000 + rep
                init_best = None
                for method in METHODS:
                    if method == "de_rand1bin":
                        start = time.perf_counter()
                        output = differential_evolution_rand1bin(
                            case.problem, population_size=100,
                            max_evaluations=BUDGET, seed=seed,
                            mutation=DE_F, crossover=DE_CR,
                        )
                        seconds = time.perf_counter()-start
                        gap = output.objective-case.optimum
                        if gap < -max(1e-8, case.optimum*1e-10):
                            raise ValueError(f"DE evaluated objective below CEC optimum F{fid}")
                        record = TrialRecord(
                            function_id=fid, function_name=case.name, dimension=30,
                            method=method, repeat=rep, seed=seed,
                            objective=output.objective, optimum=case.optimum,
                            error=max(0., gap), violation=output.violation,
                            evaluations=output.evaluations,
                            generations=output.generations,
                            coefficient_attempts=0, elapsed_seconds=seconds,
                            converged=False,
                        )
                        history = [
                            HistoryRecord(
                                function_id=fid, function_name=case.name,
                                dimension=30, method=method, repeat=rep, seed=seed,
                                generation=s.generation, evaluations=s.evaluations,
                                best_objective=s.best_objective,
                                best_error=max(0.,s.best_objective-case.optimum),
                                best_violation=s.best_violation,
                                worst_objective=s.worst_objective,
                                worst_violation=s.worst_violation,
                            ) for s in output.history
                        ]
                    else:
                        history = []
                        record = run_case(
                            case, method=method, repeat=rep, seed=seed,
                            config=paper_config(method=method, seed=seed,
                                                max_evaluations=BUDGET),
                            history_records=history, history_interval=HISTORY_INTERVAL,
                        )
                    if record.evaluations != BUDGET or not math.isfinite(record.error):
                        raise ValueError(f"F{fid} seed {seed} {method} failed exact 10k FE")
                    fes = [s.evaluations for s in history]
                    if fes != list(range(100, 10_001, 100)):
                        raise ValueError(f"F{fid} seed {seed} {method}: missing 100 checkpoints")
                    if not math.isclose(
                        history[-1].best_error, record.error,
                        rel_tol=1e-10, abs_tol=1e-6,
                    ):
                        raise ValueError("final best-so-far history/trial mismatch")
                    if any(
                        next_state.best_error > old_state.best_error + 1e-7
                        for old_state, next_state in pairwise(history)
                    ):
                        raise ValueError("best-so-far trace is not monotone")
                    if init_best is not None and not math.isclose(
                        init_best, history[0].best_error,
                        rel_tol=1e-12, abs_tol=1e-7,
                    ):
                        raise ValueError(f"F{fid} seed {seed}: initial population was not paired")
                    init_best = history[0].best_error
                    trial_writer.writerow(asdict(record))
                    hist_writer.writerows(asdict(s) for s in history)
                    tf.flush()
                    hf.flush()
                    print(
                        f"F{fid} repeat={rep} method={method} "
                        f"error={record.error:.8g} elapsed={record.elapsed_seconds:.3f}s",
                        flush=True,
                    )
    print(f"completed original function shard {shard_id}: {len(tasks)} functions")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--shard", type=int, choices=tuple(range(len(SHARDS))), required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    run(args.shard, args.output_dir)


if __name__ == "__main__":
    main()
