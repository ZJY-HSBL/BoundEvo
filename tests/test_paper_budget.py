"""Scientific guards for paired 10k-to-100k-FE optimization continuation."""

import csv
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

from boundevo.cec2017 import REFERENCE_COMMIT

ROOT = Path(__file__).resolve().parents[1]


def get_script(name):
    file = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_csv(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def make_budget_fixture(tmp_path):
    runner = get_script("run_paper_budget_case.py")
    merger = get_script("aggregate_paper_budget.py")
    source = tmp_path / "case"
    history = []
    for fid in (16, 22):
        folder = source / f"f{fid}"
        folder.mkdir(parents=True)
        env = {
            "function_id": fid, "dimension": 30,
            "methods": ["abc", "edbf", "re"], "repeats": 5,
            "evaluations": 100000, "baseline_evaluations": 10000,
            "base_seed": 20261037, "reference_commit": REFERENCE_COMMIT,
            "history_interval": 900,
        }
        (folder / "manifest.json").write_text(
            json.dumps(env), encoding="utf-8"
        )
        trials, checkpoints = [], []
        for repeat in range(5):
            for method, initial in (("abc", 10.0), ("edbf", 20.0), ("re", 30.0)):
                final = initial * 0.5
                trials.append(
                    {
                        "function_id": fid, "repeat": repeat, "method": method,
                        "seed": 20261037 + fid * 10000 + repeat,
                        "dimension": 30, "evaluations": 100000,
                        "objective": float(fid * 100) + final,
                        "optimum": float(fid * 100),
                        "error": final,
                        "elapsed_seconds": 0.5,
                        "baseline_10k_error": initial,
                        "measured_10k_error": initial,
                        "meanwhile_improvement": initial - final,
                    }
                )
                for evaluations, gap in ((100, 100), (10000, initial), (100000, final)):
                    checkpoints.append(
                        {
                            "function_id": fid, "repeat": repeat,
                            "method": method, "dimension": 30,
                            "evaluations": evaluations, "best_error": gap,
                        }
                    )
        save_csv(folder / "trials.csv", trials)
        save_csv(folder / "history.csv", checkpoints)
        history.extend(checkpoints)
    return source, history, runner, merger


def test_paper_budget_merger_verifies_30_matched_trajectories(tmp_path):
    source, history, runner, merger = make_budget_fixture(tmp_path)
    assert runner.prefix_verified(20.0, 20.0)
    assert not runner.prefix_verified(20.0, 19.0)
    assert runner.select_prefix(
        [SimpleNamespace(evaluations=100, best_error=100.0),
         SimpleNamespace(evaluations=10000, best_error=20.0)], 16, "abc"
    ) == 20
    trials, states, manifests = merger.validate(source)
    assert len(trials) == 30 and len(states) == len(history)
    assert len(manifests) == 2
    summaries = merger.summary(trials)
    assert len(summaries) == 6
    assert all(item["relative_improvement_pct"] == pytest.approx(50) for item in summaries)

    display = get_script("update_readme_results.py")
    metadata = {"repeats": 5, "evaluations": 100000}
    svg = display.paper_budget_trajectory_svg(metadata, states)
    assert ElementTree.fromstring(svg).tag.endswith("svg")
    assert "F16" in svg and "F22" in svg
    assert "100,000" in svg
    markdown = display.paper_budget_markdown(
        ROOT / "docs/experiments/cec2017-paperbudget-30d-100k-2026-10-18",
        metadata, summaries, "cn"
    )
    assert "100k" in markdown and "30 次" in markdown


def test_paper_budget_merger_rejects_changed_10k_prefix(tmp_path):
    source, _, _, merger = make_budget_fixture(tmp_path)
    path = source / "f16" / "trials.csv"
    trials = merger.read(path)
    trials[0]["baseline_10k_error"] = "999"
    save_csv(path, trials)
    with pytest.raises(ValueError, match="invalid numerical budget progression"):
        merger.validate(source)


def test_paper_budget_merger_rejects_missing_history_checkpoint(tmp_path):
    source, _, _, merger = make_budget_fixture(tmp_path)
    path = source / "f22" / "history.csv"
    checkpoints = merger.read(path)
    checkpoint = next(i for i, row in enumerate(checkpoints) if int(row["evaluations"]) == 10000)
    checkpoints.pop(checkpoint)
    save_csv(path, checkpoints)
    with pytest.raises(ValueError, match="missing or duplicated budget checkpoints"):
        merger.validate(source)
