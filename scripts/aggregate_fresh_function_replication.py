"""Fail-closed assembly of four independent-seed CEC2017 replication shards."""

# ruff: noqa: ISC004

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import sys
from collections import defaultdict
from datetime import datetime, timezone
from itertools import pairwise
from pathlib import Path

import numpy as np

from boundevo.cec2017 import REFERENCE_COMMIT

FUNCTIONS = (3, 10, 20, 30)
METHODS = ("abc", "edbf", "re")
REPEATS = 10
SEED_BASE = 20261079
BUDGET = 10_000
BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20261021


def read(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError(f"missing original evidence: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty experiment evidence: {path}")
    return rows


def save(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("cannot publish empty records")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sign_p(wins: int, losses: int) -> float:
    n = wins + losses
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(min(wins, losses) + 1)) / 2**n)


def verify(input_root: Path) -> tuple[list[dict], list[dict], list[dict]]:
    trials, history, source = [], [], []
    for fid in FUNCTIONS:
        location = input_root / f"f{fid}"
        manifest = json.loads((location / "manifest.json").read_text(encoding="utf-8"))
        expected = {
            "function_id": fid, "dimension": 30, "methods": list(METHODS),
            "repeats": REPEATS, "base_seed": SEED_BASE,
            "evaluations": BUDGET, "history_interval": 450,
            "reference_commit": REFERENCE_COMMIT,
        }
        if any(manifest.get(k) != v for k, v in expected.items()) or not manifest.get("source_commit"):
            raise ValueError(f"unverified source environment F{fid}")
        source.append(manifest)
        new_trials = read(location / "trials.csv")
        if len(new_trials) != 30:
            raise ValueError(f"F{fid} does not contain 30 original trials")
        trials.extend(new_trials)
        history.extend(read(location / "history.csv"))

    expected_keys = {(fid, rep, method) for fid in FUNCTIONS
                     for rep in range(REPEATS) for method in METHODS}
    actual = {}
    for row in trials:
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key not in expected_keys or key in actual:
            raise ValueError(f"duplicate or unexpected trial {key}")
        fid, rep, _ = key
        if (int(row["dimension"]) != 30 or int(row["evaluations"]) != BUDGET
                or int(row["seed"]) != SEED_BASE + fid * 10000 + rep):
            raise ValueError(f"incorrect seed or function evaluation budget {key}")
        if any(not math.isfinite(float(row[col]))
               for col in ("objective", "optimum", "error", "elapsed_seconds")):
            raise ValueError(f"nonfinite scientific outcome {key}")
        gap = float(row["objective"]) - float(row["optimum"])
        if gap < -1e-7 or not math.isclose(
            gap, float(row["error"]), rel_tol=1e-10, abs_tol=1e-6
        ):
            raise ValueError(f"optimizer below optimum / inconsistent error {key}")
        actual[key] = row
    if set(actual) != expected_keys or len(trials) != 120:
        raise ValueError("missing fresh-seed replicated trials")

    traces = defaultdict(list)
    for row in history:
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key not in expected_keys or not math.isfinite(float(row["best_error"])):
            raise ValueError(f"unknown / nonfinite convergence trace {key}")
        if (int(row["dimension"]) != 30
                or int(row["seed"]) != int(actual[key]["seed"])):
            raise ValueError(f"trace metadata mismatch {key}")
        traces[key].append(row)
    if set(traces) != expected_keys:
        raise ValueError("missing convergence trajectories")
    for key, rows in traces.items():
        rows.sort(key=lambda x: int(x["evaluations"]))
        x = [int(r["evaluations"]) for r in rows]
        y = [float(r["best_error"]) for r in rows]
        if (x[0] != 100 or x[-1] != BUDGET or len(set(x)) != len(x)
                or any(v < 0 for v in y)
                or any(b > a + 1e-7 for a, b in pairwise(y))
                or not math.isclose(y[-1], float(actual[key]["error"]), abs_tol=1e-6)):
            raise ValueError(f"invalid best-so-far trajectory {key}")
    for fid in FUNCTIONS:
        for rep in range(REPEATS):
            start = [float(traces[(fid, rep, m)][0]["best_error"]) for m in METHODS]
            if max(start) - min(start) > 1e-8:
                raise ValueError(f"mismatched paired initial populations F{fid} seed{rep}")
    trials.sort(key=lambda r: (int(r["function_id"]), int(r["repeat"]), r["method"]))
    history.sort(key=lambda r: (
        int(r["function_id"]), int(r["repeat"]), r["method"], int(r["evaluations"])
    ))
    return trials, history, source


def analyse(trials: list[dict]) -> tuple[list[dict], list[dict]]:
    index = {(int(t["function_id"]), int(t["repeat"]), t["method"]): t for t in trials}
    if len(index) != 120:
        raise ValueError("statistics require 120 distinct matched trials")
    summary, tests = [], []
    for fid in FUNCTIONS:
        rng = np.random.default_rng(BOOTSTRAP_SEED + fid)
        indices = rng.integers(0, REPEATS, size=(BOOTSTRAP_SAMPLES, REPEATS))
        values = {}
        for method in METHODS:
            vals = np.array([float(index[(fid, i, method)]["error"]) for i in range(REPEATS)])
            values[method] = vals
            boot = vals[indices].mean(axis=1)
            q = np.quantile(boot, [0.025, 0.975])
            summary.append({
                "function_id": fid, "method": method, "repeats": REPEATS,
                "mean_error": float(vals.mean()),
                "median_error": float(np.median(vals)),
                "std_error": float(vals.std(ddof=1)),
                "ci95_low": float(q[0]), "ci95_high": float(q[1]),
                "mean_elapsed_seconds": float(np.mean(
                    [float(index[(fid, i, method)]["elapsed_seconds"]) for i in range(REPEATS)]
                )),
            })
        for other in ("edbf", "re"):
            a, b = values["abc"], values[other]
            wins = int(np.count_nonzero(a < b - 1e-9))
            losses = int(np.count_nonzero(a > b + 1e-9))
            delta = np.log1p(b) - np.log1p(a)
            q = np.quantile(delta[indices].mean(axis=1), [0.025, 0.975])
            tests.append({
                "function_id": fid, "contrast": f"abc_vs_{other}",
                "abc_wins": wins, "abc_losses": losses,
                "ties": REPEATS - wins - losses,
                "mean_paired_log_advantage": float(delta.mean()),
                "ci95_low": float(q[0]), "ci95_high": float(q[1]),
                "sign_p": sign_p(wins, losses), "holm_p": 1.0,
            })
    adjusted = 0.0
    for rank, idx in enumerate(sorted(range(len(tests)), key=lambda i: tests[i]["sign_p"])):
        adjusted = max(adjusted, min(1.0, tests[idx]["sign_p"] * (len(tests) - rank)))
        tests[idx]["holm_p"] = adjusted
    return summary, tests


def render_report(summary: list[dict], tests: list[dict]) -> str:
    out = [
        "# Fresh-seed CEC2017 cross-function replication (exploratory)",
        "",
        "F3/F10/F20/F30, D=30, 10,000 objective evaluations per run, ABC/EDBF/RE, "
        "10 **new paired random seeds** for each function. The cohort is disjoint from "
        "the earlier F16/F22 seed cohort. All 120 trials used a fixed optimizer.",
        "",
        "Functions were selected after inspecting previous results: new seeds improve "
        "replication but this is **not a preregistered selection-blind benchmark**. "
        "The four functions do not represent a random sample of CEC2017.",
        "",
        "## Measured final objective gaps (lower is better)",
        "",
        "| Function | Method | Mean | Median | Std dev | Bootstrap mean 95% CI |",
        "|:---|:---|---:|---:|---:|:---|",
    ]
    for r in summary:
        out.append(
            f"| F{r['function_id']} | {r['method'].upper()} | "
            f"{r['mean_error']:.6g} | {r['median_error']:.6g} | {r['std_error']:.5g} | "
            f"[{r['ci95_low']:.6g}, {r['ci95_high']:.6g}] |"
        )
    out.extend([
        "",
        "## Paired exact sign tests",
        "",
        "| Function | Contrast | ABC W/L/T | raw p | Holm p (8 tests) |",
        "|:---|:---|---:|---:|---:|",
    ])
    for r in tests:
        out.append(
            f"| F{r['function_id']} | {r['contrast']} | "
            f"{r['abc_wins']}/{r['abc_losses']}/{r['ties']} | "
            f"{r['sign_p']:.6g} | {r['holm_p']:.6g} |"
        )
    out.extend([
        "",
        "The sign test measures paired direction, not a comparison of mean objective "
        "errors. Holm adjustment is limited to these eight exploratory tests; "
        "earlier research selection is not covered. Bootstrap percentile intervals "
        "are based on 10,000 paired-seed resamples.",
        "",
        "## Original evidence",
        "",
        "[120 trials](trials.csv) · [convergence history](history.csv) · "
        "[summary](summary.csv) · [paired tests](paired_tests.csv) · "
        "[reference commit and seed source](environment.json)",
        "",
    ])
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()
    trials, history, sources = verify(args.input_dir)
    summary, tests = analyse(trials)
    dest = args.output_dir
    save(dest / "trials.csv", trials)
    save(dest / "history.csv", history)
    save(dest / "summary.csv", summary)
    save(dest / "paired_tests.csv", tests)
    manifest = {
        "functions": list(FUNCTIONS), "methods": list(METHODS),
        "dimension": 30, "repeats": REPEATS, "evaluations": BUDGET,
        "base_seed": SEED_BASE, "trials": len(trials), "history_rows": len(history),
        "reference_commit": REFERENCE_COMMIT, "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED, "exploratory_function_selection": True,
        "seed_independent_of_previous_cohorts": True,
        "source_manifests": sources, "python": sys.version, "numpy": np.__version__,
        "platform": platform.platform(), "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (dest / "environment.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (dest / "report.md").write_text(render_report(summary, tests), encoding="utf-8")
    print(f"Validated {len(trials)} new original optimizer trials, "
          f"{len(history)} convergence checkpoints, {len(tests)} Holm contrasts.")


if __name__ == "__main__":
    main()
