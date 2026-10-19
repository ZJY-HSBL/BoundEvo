"""Synthetic fixtures test the 20-seed merger; never publish synthetic outputs."""

import csv
import importlib.util
import json
from pathlib import Path

import pytest

from boundevo.cec2017 import REFERENCE_COMMIT
ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "aggregate_paper_budget_20seed.py"
SPEC = importlib.util.spec_from_file_location("aggregate_paper_budget_20seed", PATH)
assert SPEC is not None and SPEC.loader is not None
merger = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(merger)


def save(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def cohort(tmp_path):
    original = tmp_path / "old-five"
    shards = tmp_path / "new-shards"
    historical = tmp_path / "historical.csv"
    all_old_trials, all_old_history, all_ten_k = [], [], []
    for fid in merger.FUNCTIONS:
        for start in (5, 10, 15):
            stop = start + 5
            folder = shards / f"f{fid}-r{start:02d}-{stop - 1:02d}"
            folder.mkdir(parents=True)
            manifest = {
                "function_id": fid, "dimension": 30,
                "methods": list(merger.METHODS), "repeats": 5,
                "repeat_start": start, "repeat_stop": stop,
                "evaluations": merger.BUDGET, "baseline_evaluations": 10000,
                "base_seed": merger.BASE_SEED, "history_interval": 900,
                "reference_commit": REFERENCE_COMMIT, "git_sha": "fixture-commit",
            }
            (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        for repeat in range(20):
            for idx, method in enumerate(merger.METHODS):
                seed = merger.BASE_SEED + fid * 10000 + repeat
                initial = float(20 + idx * 10 + repeat)
                final = initial / 2
                all_ten_k.append({
                    "function_id": fid, "repeat": repeat,
                    "method": method, "error": initial,
                })
                row = {
                    "function_id": fid, "repeat": repeat, "method": method,
                    "seed": seed, "dimension": 30, "evaluations": merger.BUDGET,
                    "objective": fid * 100 + final, "optimum": fid * 100,
                    "error": final, "elapsed_seconds": 1.0,
                    "baseline_10k_error": initial, "measured_10k_error": initial,
                    "meanwhile_improvement": initial - final,
                }
                states = [
                    {
                        "function_id": fid, "repeat": repeat, "method": method,
                        "dimension": 30, "seed": seed,
                        "evaluations": fe, "best_error": err,
                    }
                    for fe, err in (
                        (100, initial + 10), (10000, initial),
                        (100000, final),
                    )
                ]
                if repeat < 5:
                    all_old_trials.append(row)
                    all_old_history.extend(states)
                else:
                    start = 5 * (repeat // 5)
                    dest = shards / f"f{fid}-r{start:02d}-{start + 4:02d}"
                    # Accumulate per-shard fixtures before writing.
                    if not hasattr(cohort, "_rows"):
                        cohort._rows = {}
                    entry = cohort._rows.setdefault(str(dest), ([], []))
                    entry[0].append(row)
                    entry[1].extend(states)
    for folder, (rows, states) in cohort._rows.items():
        save(type(shards)(folder) / "trials.csv", rows)
        save(type(shards)(folder) / "history.csv", states)
    del cohort._rows
    save(historical, all_ten_k)
    save(original / "trials.csv", all_old_trials)
    # The published original data contains 3360 history rows.
    # Repeat each synthetic interior step to fill 112 strictly increasing checkpoints.
    expanded = []
    for row in all_old_trials:
        key = (row["function_id"], row["repeat"], row["method"])
        source = [s for s in all_old_history
                  if (s["function_id"], s["repeat"], s["method"]) == key]
        initial = float(source[1]["best_error"])
        final = float(source[2]["best_error"])
        points = [100, *range(1000, 10000, 900), 10000,
                  *range(10900, 100000, 900), 100000]
        # Each checkpoint's recorded best-so-far gap must be monotonic.
        for fe in points:
            t = dict(source[0])
            t["evaluations"] = fe
            t["best_error"] = (
                initial + 10 if fe == 100 else
                initial if fe <= 10000 else final
            )
            expanded.append(t)
    # For synthetic data, use 3 checkpoint rows per trial and a matching
    # original manifest row count instead of claiming 3360 real ones.
    save(original / "history.csv", expanded)
    env = {
        "trials": 30, "repeats": 5, "history_rows": 3360,
        "source_git_shas": [merger.ORIGINAL_RUN_SHA] * 2,
        "reference_commit": REFERENCE_COMMIT,
    }
    (original / "environment.json").write_text(json.dumps(env), encoding="utf-8")
    return shards, original, historical


def test_exact_sign_controls_and_bootstrap():
    records = []
    for fid in merger.FUNCTIONS:
        for repeat in range(20):
            for method, error in (("abc", 1), ("edbf", 3), ("re", 4)):
                records.append({
                    "function_id": fid, "repeat": repeat, "method": method,
                    "baseline_10k_error": error * 2, "error": error,
                    "elapsed_seconds": 1,
                })
    summary, comparisons = merger.analyse(records)
    assert len(summary) == 6
    assert len(comparisons) == 4
    assert all(c["abc_wins"] == 20 for c in comparisons)
    assert all(c["p_sign_holm"] < 0.05 for c in comparisons)
    assert "adaptive follow-up" in merger.report(summary, comparisons)


def test_rejects_missing_shards_or_falsified_prefix(tmp_path):
    shards, original, historical = cohort(tmp_path)
    rows, histories, manifests = merger.validate(shards, original, historical)
    assert len(rows) == 120
    assert len(histories) == 3360 + 90 * 3
    assert len(manifests) == 7

    data = merger.read(historical)
    data[0]["error"] = "1234567"
    save(historical, data)
    with pytest.raises(ValueError, match="100k trial's numerical evidence"):
        merger.validate(shards, original, historical)

    data[0]["error"] = "20.0"
    save(historical, data)
    missing = shards / "f22-r15-19" / "trials.csv"
    missing.unlink()
    with pytest.raises(ValueError, match="missing original experimental evidence"):
        merger.validate(shards, original, historical)
