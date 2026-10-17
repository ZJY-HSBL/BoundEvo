"""Execute a resumable, real CEC2017 full-suite experiment shard.

Shard assignment depends only on official function IDs and shard count. Each
completed trial and its sampled convergence history are appended immediately,
so partial artifacts remain inspectable after a worker failure.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import asdict, fields
from pathlib import Path

from boundevo.cec2017 import PAPER_FUNCTION_IDS, REFERENCE_COMMIT, make_cec2017_case
from boundevo.experiments import HistoryRecord, TrialRecord, paper_config, run_case


def shard_function_ids(index: int, count: int) -> tuple[int, ...]:
    if count < 1 or not 0 <= index < count:
        raise ValueError("shard index must be in [0, shard count)")
    return tuple(fid for offset, fid in enumerate(PAPER_FUNCTION_IDS) if offset % count == index)


def _open_writer(path: Path, columns: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("w", encoding="utf-8", newline="")
    writer = csv.DictWriter(handle, fieldnames=columns)
    writer.writeheader()
    handle.flush()
    return handle, writer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, default=4)
    parser.add_argument("--dimension", type=int, default=30)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--evaluations", type=int, default=10000)
    parser.add_argument("--history-interval", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261017)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.repeats < 1 or args.evaluations < 100 or args.history_interval < 1:
        parser.error("repeats>=1, evaluations>=100 and history_interval>=1 required")
    functions = shard_function_ids(args.shard_index, args.shard_count)
    if not functions:
        parser.error("shard contains no CEC2017 function IDs")

    target = args.output_dir
    target.mkdir(parents=True, exist_ok=True)
    manifest = {
        "index": args.shard_index,
        "count": args.shard_count,
        "function_ids": functions,
        "dimension": args.dimension,
        "repeats": args.repeats,
        "evaluations": args.evaluations,
        "history_interval": args.history_interval,
        "base_seed": args.seed,
        "methods": ["abc", "edbf", "re"],
        "reference_commit": REFERENCE_COMMIT,
        "git_sha": os.getenv("GITHUB_SHA"),
    }
    (target / "shard_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    trial_columns = [field.name for field in fields(TrialRecord)] + ["attempts_per_offspring"]
    history_columns = [field.name for field in fields(HistoryRecord)]
    trial_handle, trial_writer = _open_writer(target / "trials.csv", trial_columns)
    history_handle, history_writer = _open_writer(target / "history.csv", history_columns)
    total = 0
    try:
        for fid in functions:
            case = make_cec2017_case(fid, args.dimension, backend="reference")
            for repeat in range(args.repeats):
                seed = args.seed + fid * 10_000 + repeat
                for method in ("abc", "edbf", "re"):
                    states: list[HistoryRecord] = []
                    result = run_case(
                        case,
                        method=method,
                        repeat=repeat,
                        seed=seed,
                        config=paper_config(
                            method=method,
                            seed=seed,
                            max_evaluations=args.evaluations,
                        ),
                        history_records=states,
                        history_interval=args.history_interval,
                    )
                    if result.evaluations != args.evaluations:
                        raise RuntimeError(
                            f"early convergence F{fid}/{repeat}/{method}: "
                            f"{result.evaluations} != {args.evaluations}"
                        )
                    if not states or states[0].evaluations != 100:
                        raise RuntimeError("missing initial convergence checkpoint")
                    if states[-1].evaluations != args.evaluations:
                        raise RuntimeError("missing final convergence checkpoint")
                    row = asdict(result)
                    row["attempts_per_offspring"] = (
                        result.coefficient_attempts / (result.evaluations - 100)
                    )
                    trial_writer.writerow(row)
                    trial_handle.flush()
                    history_writer.writerows(asdict(state) for state in states)
                    history_handle.flush()
                    total += 1
                    print(
                        f"shard={args.shard_index} {total}/{len(functions)*args.repeats*3} "
                        f"F{fid} seed={seed} {method} "
                        f"FE={result.evaluations} error={result.error:.7g} "
                        f"sec={result.elapsed_seconds:.2f} checkpoints={len(states)}",
                        flush=True,
                    )
    finally:
        trial_handle.close()
        history_handle.close()
    expected = len(functions) * args.repeats * 3
    if total != expected:
        raise RuntimeError(f"shard {args.shard_index}: expected {expected}, got {total}")


if __name__ == "__main__":
    main()
