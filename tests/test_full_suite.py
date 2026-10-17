"""Regression tests for all-29-function 10k-FE sharding and evidence plots."""

import csv
import importlib.util
import json
from pathlib import Path
from xml.etree import ElementTree

import pytest

from boundevo.cec2017 import PAPER_FUNCTION_IDS, REFERENCE_COMMIT

ROOT = Path(__file__).resolve().parents[1]


def load_script(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename.replace(".py", ""), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_shards_partition_all_29_without_overlap():
    runner = load_script("run_full_suite_shard.py")
    parts = [runner.shard_function_ids(i, 4) for i in range(4)]
    assert sum(map(len, parts)) == 29
    assert set().union(*[set(part) for part in parts]) == set(PAPER_FUNCTION_IDS)
    assert all(set(a).isdisjoint(b) for i, a in enumerate(parts) for b in parts[i+1:])
    with pytest.raises(ValueError):
        runner.shard_function_ids(4, 4)


def test_merge_rejects_missing_and_duplicate_shard_trials(tmp_path):
    merger = load_script("merge_full_suite.py")
    runner = load_script("run_full_suite_shard.py")
    input_dir = tmp_path / "parts"
    for shard in range(4):
        folder = input_dir / f"shard-{shard}"
        folder.mkdir(parents=True)
        ids = runner.shard_function_ids(shard, 4)
        manifest = {
            "index": shard, "count": 4, "function_ids": ids,
            "methods": ["abc", "edbf", "re"], "dimension": 30,
            "evaluations": 10000, "repeats": 1, "history_interval": 500,
            "base_seed": 20261017, "reference_commit": REFERENCE_COMMIT,
        }
        (folder / "shard_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        trials = []
        history = []
        for fid in ids:
            for method, error in (("abc", 10), ("edbf", 20), ("re", 30)):
                seed = 20261017 + fid * 10000
                optimum = float(fid * 100)
                trials.append(
                    {
                        "function_id": fid, "repeat": 0, "method": method,
                        "seed": seed, "dimension": 30, "evaluations": 10000,
                        "objective": optimum + error, "optimum": optimum,
                        "error": error, "elapsed_seconds": 0.1,
                        "attempts_per_offspring": 1.0,
                    }
                )
                for evaluations, val in ((100, 500.0), (10000, error)):
                    history.append(
                        {
                            "function_id": fid, "repeat": 0, "method": method,
                            "dimension": 30, "evaluations": evaluations,
                            "best_objective": optimum + val,
                            "best_error": val, "worst_objective": optimum + val + 20,
                        }
                    )
        write_csv(folder / "trials.csv", trials)
        write_csv(folder / "history.csv", history)
    trials, states, _ = merger.aggregate(input_dir, 4, 1, 10000)
    assert len(trials) == 87
    assert len(states) == 174
    summary = merger.summaries(trials, 1)
    assert len(summary) == 87
    assert all(int(row["mean_evaluations"]) == 10000 for row in summary)

    shard = input_dir / "shard-0" / "trials.csv"
    rows = merger.load_csv(shard)
    rows.pop()
    write_csv(shard, rows)
    with pytest.raises(ValueError, match="incomplete trial coverage"):
        merger.aggregate(input_dir, 4, 1, 10000)


def test_fullsuite_winner_and_convergence_images_are_valid_svg():
    generator = load_script("update_readme_results.py")
    ids = [1, *range(3, 31)]
    env = {
        "functions": ids, "dimension": 30, "repeats": 3, "evaluations": 10000,
    }
    means = []
    for fid in ids:
        for method, err in (("abc", 10), ("edbf", 20), ("re", 30)):
            means.append(
                {"function_id": fid, "method": method, "mean_error": err, "repeats": 3}
            )
    svg = generator.screening_svg(env, means)
    assert ElementTree.fromstring(svg).tag.endswith("svg")

    checkpoints = []
    for fid in (10, 20, 22, 30):
        for method in ("abc", "edbf", "re"):
            for rep in range(3):
                for fe, error in ((100, 1000), (5100, 100), (10000, 10)):
                    checkpoints.append(
                        {
                            "function_id": fid, "method": method, "repeat": rep,
                            "evaluations": fe, "best_error": error,
                        }
                    )
    convergence = generator.fullsuite_convergence_svg(checkpoints, env)
    assert ElementTree.fromstring(convergence).tag.endswith("svg")
    for fid in (10, 20, 22, 30):
        assert f"F{fid}" in convergence

    tests = [
        {
            "comparison": f"abc_vs_{method}", "wins": 29, "losses": 0,
            "raw_p": 0.000001, "holm_p": 0.000002,
        }
        for method in ("edbf", "re")
    ]
    markdown = generator.fullsuite_markdown(
        ROOT / "docs/experiments/cec2017-fullsuite-30d-10k-2026-10-17",
        env, means, tests, "cn"
    )
    assert "收敛" in markdown
    assert "261 次" in markdown
    assert "Holm" in markdown


def test_budget_leader_transitions_are_derived_from_mean_errors():
    generator = load_script("update_readme_results.py")
    env = {
        "functions": [1, *range(3, 31)], "dimension": 30,
        "repeats": 3, "base_seed": 20261017,
        "reference_commit": REFERENCE_COMMIT,
    }
    early = {**env, "evaluations": 1200}
    later = {**env, "evaluations": 10000}
    old_data = []
    new_data = []
    for fid in env["functions"]:
        old_winner = "re" if fid in (20, 22) else "abc"
        for method in ("abc", "edbf", "re"):
            old_data.append(
                {
                    "function_id": fid, "method": method,
                    "mean_error": 1.0 if method == old_winner else 9.0,
                }
            )
            new_data.append(
                {"function_id": fid, "method": method,
                 "mean_error": 1.0 if method == "abc" else 9.0}
            )
    matrix, changed = generator.leader_transition_counts(
        early, old_data, later, new_data
    )
    assert changed == 2
    assert matrix[("abc", "abc")] == 27
    assert matrix[("re", "abc")] == 2
    assert sum(matrix.values()) == 29
    svg = generator.leader_transition_svg(early, old_data, later, new_data)
    assert ElementTree.fromstring(svg).tag.endswith("svg")
    assert "2 of 29" in svg
