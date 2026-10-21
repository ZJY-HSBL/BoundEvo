"""Compute frozen CEC2017 DE calibration and fresh-seed evaluation cohorts.

Each mode writes REAL objective-evaluation evidence, not display/demo data.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import time
from dataclasses import asdict, fields
from itertools import pairwise
from pathlib import Path

from boundevo.cec2017 import PAPER_FUNCTION_IDS, REFERENCE_COMMIT, make_cec2017_case
from boundevo.de_baseline import differential_evolution_jde, differential_evolution_rand1bin
from boundevo.experiments import HistoryRecord, TrialRecord, paper_config, run_case

DEV_FUNCTIONS = (3, 10, 20, 30)
TEST_FUNCTIONS = tuple(fid for fid in PAPER_FUNCTION_IDS if fid not in DEV_FUNCTIONS)
TEST_SHARDS = tuple(tuple(TEST_FUNCTIONS[i:i+5]) for i in range(0, 25, 5))
CANDIDATES = (
    ("rand050cr090", "rand1bin", 0.5, 0.9),
    ("rand080cr030", "rand1bin", 0.8, 0.3),
    ("rand080cr090", "rand1bin", 0.8, 0.9),
    ("best050cr090", "best1bin", 0.5, 0.9),
    ("best080cr030", "best1bin", 0.8, 0.3),
    ("best080cr090", "best1bin", 0.8, 0.9),
)
DEV_SEED = 20262101
TEST_SEED = 20262201
EVAL_METHODS = ("abc", "de_tuned", "jde")
BUDGET = 10_000
POPULATION = 100


def write_run(
    case, method: str, repeat: int, seed: int, *,
    candidate: tuple | None,
    trials: csv.DictWriter,
    histories: csv.DictWriter,
) -> None:
    history: list[HistoryRecord]
    if method == "abc":
        history = []
        trial = run_case(
            case, method="abc", repeat=repeat, seed=seed,
            config=paper_config(method="abc", max_evaluations=BUDGET, seed=seed),
            history_records=history, history_interval=100,
        )
    else:
        start = time.perf_counter()
        if method == "jde":
            result = differential_evolution_jde(
                case.problem, seed=seed, population_size=POPULATION,
                max_evaluations=BUDGET,
            )
        else:
            if candidate is None:
                raise ValueError("calibrated DE requires the frozen candidate")
            _, strategy, mutation, crossover = candidate
            result = differential_evolution_rand1bin(
                case.problem, seed=seed, population_size=POPULATION,
                max_evaluations=BUDGET, strategy=strategy,
                mutation=mutation, crossover=crossover,
            )
        elapsed = time.perf_counter() - start
        gap = result.objective - case.optimum
        if gap < -max(1e-8, case.optimum * 1e-10):
            raise ValueError(f"F{case.function_id} objective below CEC optimum")
        trial = TrialRecord(
            function_id=case.function_id, function_name=case.name, dimension=30,
            method=method, repeat=repeat, seed=seed,
            objective=result.objective, optimum=case.optimum, error=max(0., gap),
            violation=result.violation, evaluations=result.evaluations,
            generations=result.generations, coefficient_attempts=0,
            elapsed_seconds=elapsed, converged=False,
        )
        history = [
            HistoryRecord(
                function_id=case.function_id, function_name=case.name,
                dimension=30, method=method, repeat=repeat, seed=seed,
                generation=state.generation, evaluations=state.evaluations,
                best_objective=state.best_objective,
                best_error=max(0., state.best_objective-case.optimum),
                best_violation=state.best_violation,
                worst_objective=state.worst_objective,
                worst_violation=state.worst_violation,
            )
            for state in result.history
        ]
    if trial.evaluations != BUDGET or len(history) != 100:
        raise ValueError(f"{method} failed exact 10k FE and 100 checkpoints")
    if [h.evaluations for h in history] != list(range(100, 10_001, 100)):
        raise ValueError(f"{method} did not record exact 100-FE grid")
    if any(b.best_error > a.best_error + 1e-7 for a, b in pairwise(history)):
        raise ValueError(f"{method} best-so-far history not monotone")
    if not math.isclose(
        history[-1].best_error, trial.error, rel_tol=1e-10, abs_tol=1e-6
    ):
        raise ValueError("original trial and best-so-far endpoint disagreement")
    trials.writerow(asdict(trial))
    histories.writerows(asdict(h) for h in history)
    print(
        f"F{case.function_id} {method} seed={seed} "
        f"error={trial.error:.8g} elapsed={trial.elapsed_seconds:.3f}s",
        flush=True,
    )


def run(phase: str, task: int, out: Path, selection_file: Path | None) -> None:
    if phase == "development":
        if task not in DEV_FUNCTIONS or selection_file:
            raise ValueError("invalid development function task")
        fids = (task,)
        methods = [c[0] for c in CANDIDATES]
        repeats = 3
        seed_start = DEV_SEED
        selection = None
    elif phase == "evaluation":
        if not 0 <= task < len(TEST_SHARDS) or selection_file is None:
            raise ValueError("invalid heldout task/selection path")
        selection = json.loads(selection_file.read_text(encoding="utf-8"))
        allowed = {c[0]: c for c in CANDIDATES}
        if (selection.get("selected") not in allowed
                or selection.get("development_functions") != list(DEV_FUNCTIONS)
                or selection.get("calibration_trials") != 72
                or not selection.get("calibration_source_commit")):
            raise ValueError("unverified frozen development-only calibration selection")
        choice = allowed[selection["selected"]]
        if (selection.get("strategy") != choice[1]
                or selection.get("mutation") != choice[2]
                or selection.get("crossover") != choice[3]):
            raise ValueError("tampered selected DE parameter configuration")
        fids = TEST_SHARDS[task]
        methods = list(EVAL_METHODS)
        repeats = 10
        seed_start = TEST_SEED
    else:
        raise ValueError("unknown phase")
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "phase": phase, "task_id": task, "functions": list(fids),
        "methods": methods, "dimension": 30, "repeats": repeats,
        "seed_base": seed_start, "evaluations": BUDGET,
        "population": POPULATION, "history_step_fe": 100,
        "reference_commit": REFERENCE_COMMIT,
        "source_commit": os.environ.get("GITHUB_SHA"),
        "calibration_source_commit": selection["calibration_source_commit"] if selection else None,
        "selected_de": selection,
        "science_protocol": "docs/calibrated_de_jde_protocol.md",
    }
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n",encoding="utf-8")
    with ((out/"trials.csv").open("w",encoding="utf-8",newline="") as file,
          (out/"history.csv").open("w",encoding="utf-8",newline="") as hf):
        writer = csv.DictWriter(file, fieldnames=[f.name for f in fields(TrialRecord)])
        history_writer = csv.DictWriter(
            hf, fieldnames=[f.name for f in fields(HistoryRecord)]
        )
        writer.writeheader()
        history_writer.writeheader()
        for fid in fids:
            case = make_cec2017_case(fid, 30, backend="reference")
            for repeat in range(repeats):
                seed = seed_start + 10000*fid + repeat
                same_initial = None
                for method in methods:
                    if phase == "development":
                        candidate = next(c for c in CANDIDATES if c[0] == method)
                    elif method == "de_tuned":
                        candidate = choice
                    else:
                        candidate = None
                    # A memory-light one-run buffer allows exact within-seed
                    # initialization equivalence checks before accepting data.
                    tmp = io.StringIO(newline="")
                    th = io.StringIO(newline="")
                    local = csv.DictWriter(
                        tmp, fieldnames=[f.name for f in fields(TrialRecord)]
                    )
                    local_hist = csv.DictWriter(
                        th, fieldnames=[f.name for f in fields(HistoryRecord)]
                    )
                    write_run(
                        case, method, repeat, seed,
                        candidate=candidate,
                        trials=local, histories=local_hist,
                    )
                    trial_row = next(csv.DictReader(
                        io.StringIO(",".join([f.name for f in fields(TrialRecord)]) +
                                    "\n" + tmp.getvalue())
                    ))
                    history_rows = list(csv.DictReader(
                        io.StringIO(",".join([f.name for f in fields(HistoryRecord)]) +
                                    "\n" + th.getvalue())
                    ))
                    initial = float(history_rows[0]["best_error"])
                    if same_initial is not None and not math.isclose(
                        same_initial, initial, rel_tol=1e-12, abs_tol=1e-7
                    ):
                        raise ValueError(f"F{fid} repeat{repeat}: initial populations differ")
                    same_initial = initial
                    writer.writerow(trial_row)
                    history_writer.writerows(history_rows)
                    file.flush()
                    hf.flush()
    print(f"Completed {phase} task={task}, functions={fids}")


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--phase",choices=("development","evaluation"),required=True)
    p.add_argument("--task",type=int,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--selection",type=Path)
    args=p.parse_args()
    run(args.phase,args.task,args.output_dir,args.selection)


if __name__ == "__main__":
    main()
