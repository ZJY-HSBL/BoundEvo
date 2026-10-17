"""Fresh, nonoverlapping seed holdout: integrity, inference, and real-data SVG."""

import csv
import importlib.util
import json
from pathlib import Path
from xml.etree import ElementTree

import pytest

from boundevo.cec2017 import REFERENCE_COMMIT

ROOT = Path(__file__).resolve().parents[1]


def load_script(filename):
    location = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), location)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def fixture(tmp_path):
    agg = load_script("aggregate_seed_holdout.py")
    folder = tmp_path / "fresh"
    for fid in agg.FUNCTIONS:
        target = folder / f"f{fid}"
        target.mkdir(parents=True)
        manifest = {
            "functions": [fid], "dimension": 30, "repeats": 20,
            "evaluations": 10000, "base_seed": 20261037,
            "reference_commit": REFERENCE_COMMIT, "git_sha": "fixture-commit",
        }
        (target / "environment.json").write_text(json.dumps(manifest), encoding="utf-8")
        checks = [
            {"function_id": f, "dimension": d, "status": "pass"}
            for d in (10, 30) for f in [1, *range(3, 31)]
        ]
        save(target / "backend_preflight.csv", checks)
        trials = []
        for repeat in range(20):
            for method, gap in (("abc", 1.0), ("edbf", 5.0), ("re", 4.0)):
                trials.append(
                    {
                        "function_id": fid, "repeat": repeat, "method": method,
                        "seed": 20261037 + fid * 10000 + repeat,
                        "dimension": 30, "evaluations": 10000, "generations": 9900,
                        "objective": fid * 100.0 + gap, "optimum": fid * 100.0,
                        "error": gap, "elapsed_seconds": 0.123,
                        "attempts_per_offspring": 1.0,
                    }
                )
        save(target / "trials.csv", trials)
    return folder


def test_holdout_seed_pairing_exact_sign_and_bootstrap(tmp_path):
    module = load_script("aggregate_seed_holdout.py")
    folder = fixture(tmp_path)
    rows, manifests = module.validate(folder)
    assert len(rows) == 120
    assert len(manifests) == 2
    summary, comparisons = module.summarize(rows)
    assert len(summary) == 6
    assert len(comparisons) == 4
    assert all(row["abc_wins"] == 20 and row["abc_losses"] == 0 for row in comparisons)
    assert all(row["p_sign_holm"] < 0.05 for row in comparisons)
    assert all(row["paired_log1p_ci95_low"] > 0 for row in comparisons)
    assert module.exact_sign_p(0, 20) == pytest.approx(2 / 2**20)
    assert "Twenty **new**" in module.report(summary, comparisons)


def test_holdout_rejects_duplicate_seed_or_missing_trial(tmp_path):
    module = load_script("aggregate_seed_holdout.py")
    folder = fixture(tmp_path)
    one = folder / "f16" / "trials.csv"
    data = module.read_csv(one)
    data[0]["seed"] = "0"
    save(one, data)
    with pytest.raises(ValueError, match="wrong seed"):
        module.validate(folder)
    data[0]["seed"] = str(20261037 + 16 * 10000)
    save(one, data[:-1])
    with pytest.raises(ValueError, match="incomplete trial"):
        module.validate(folder)


def test_holdout_plot_and_markdown_parse_from_test_data(tmp_path):
    source = load_script("aggregate_seed_holdout.py")
    view = load_script("update_readme_results.py")
    folder = fixture(tmp_path)
    rows, _ = source.validate(folder)
    summary, comparisons = source.summarize(rows)
    experiment = ROOT / "docs/experiments/cec2017-holdout-30d-10k-2026-10-17"
    plot = view.fresh_seed_holdout_svg({"repeats": 20}, summary)
    assert ElementTree.fromstring(plot).tag.endswith("svg")
    assert "F16" in plot and "F22" in plot
    assert "95% bootstrap" in plot
    text = view.fresh_seed_holdout_markdown(
        experiment, {"repeats": 20}, summary, comparisons, "cn"
    )
    assert "120 次" in text
    assert "Holm" in text
    assert "cec2017-holdout-30d-10k-2026-10-17/trials.csv" in text
