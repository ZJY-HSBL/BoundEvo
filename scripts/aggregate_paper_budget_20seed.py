"""Merge 20 matched 100k-FE seeds without rerunning the five published seeds.

This is an *adaptive extension* motivated by the high F22 variance observed
in the initial five-seed 100k experiment. It is not a fresh independent cohort.
"""

# ruff: noqa: ISC004

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from itertools import pairwise
from pathlib import Path

import numpy as np

from boundevo.cec2017 import REFERENCE_COMMIT

FUNCTIONS = (16, 22)
METHODS = ("abc", "edbf", "re")
REPEATS = 20
BASE_SEED = 20261037
BUDGET = 100_000
BOOTSTRAP_REPS = 10_000
BOOTSTRAP_SEED = 20261019
ORIGINAL_RUN_SHA = "66a5c36288772260543ec59cacbb37edfd5f8b14"


def exact_sign_p(wins: int, losses: int) -> float:
    """Exact two-sided binomial sign test, ignoring paired ties."""

    n = wins + losses
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(min(wins, losses) + 1)) / 2**n)


def read(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError(f"missing original experimental evidence: {path}")
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("refusing to publish an empty dataset")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def validate(
    shards: Path, published_five: Path, previous_ten_k: Path
) -> tuple[list[dict], list[dict], list[dict]]:
    """Reject absent shards, duplicate seeds, changed history, and fake prefixes."""

    original_env = json.loads((published_five / "environment.json").read_text("utf-8"))
    if (
        original_env.get("trials") != 30
        or original_env.get("repeats") != 5
        or original_env.get("history_rows") != 3360
        or original_env.get("source_git_shas") != [ORIGINAL_RUN_SHA] * 2
        or original_env.get("reference_commit") != REFERENCE_COMMIT
    ):
        raise ValueError("published original five-seed source is unverified")
    old_trials = read(published_five / "trials.csv")
    old_history = read(published_five / "history.csv")
    if len(old_trials) != 30 or len(old_history) != 3360:
        raise ValueError("incomplete published five-seed original evidence")

    prior = {}
    for row in read(previous_ten_k):
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key in prior:
            raise ValueError(f"duplicate original 10k result: {key}")
        prior[key] = float(row["error"])
    expected = {
        (fid, repeat, method)
        for fid in FUNCTIONS
        for repeat in range(REPEATS)
        for method in METHODS
    }
    if set(prior) != expected:
        raise ValueError("historical 20-seed 10k trial keys are incomplete")

    trials = list(old_trials)
    history = list(old_history)
    manifests = [original_env]
    for fid in FUNCTIONS:
        for start in (5, 10, 15):
            stop = start + 5
            shard = shards / f"f{fid}-r{start:02d}-{stop - 1:02d}"
            manifest = json.loads((shard / "manifest.json").read_text("utf-8"))
            constraints = {
                "function_id": fid,
                "dimension": 30,
                "methods": list(METHODS),
                "repeats": 5,
                "repeat_start": start,
                "repeat_stop": stop,
                "evaluations": BUDGET,
                "baseline_evaluations": 10000,
                "base_seed": BASE_SEED,
                "history_interval": 900,
                "reference_commit": REFERENCE_COMMIT,
            }
            if any(manifest.get(key) != value for key, value in constraints.items()):
                raise ValueError(f"shard manifest disagrees with protocol: {shard.name}")
            if not manifest.get("git_sha"):
                raise ValueError(f"missing source commit provenance: {shard.name}")
            trials.extend(read(shard / "trials.csv"))
            history.extend(read(shard / "history.csv"))
            manifests.append(manifest)

    observed = {}
    for row in trials:
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key not in expected or key in observed:
            raise ValueError(f"duplicate/unexpected 100k trial: {key}")
        fid, repeat, _ = key
        if (
            int(row["seed"]) != BASE_SEED + fid * 10000 + repeat
            or int(row["dimension"]) != 30
            or int(row["evaluations"]) != BUDGET
        ):
            raise ValueError(f"100k trial's seed, dimension or budget differs: {key}")
        numbers = (
            "objective", "optimum", "error", "elapsed_seconds",
            "baseline_10k_error", "measured_10k_error", "meanwhile_improvement",
        )
        if any(not math.isfinite(float(row[name])) for name in numbers):
            raise ValueError(f"nonfinite trial evidence: {key}")
        objective_gap = float(row["objective"]) - float(row["optimum"])
        if (
            objective_gap < -1e-7
            or not math.isclose(objective_gap, float(row["error"]), abs_tol=1e-6)
            or not math.isclose(float(row["baseline_10k_error"]), prior[key],
                                rel_tol=1e-9, abs_tol=1e-6)
            or not math.isclose(float(row["measured_10k_error"]), prior[key],
                                rel_tol=1e-9, abs_tol=1e-6)
            or not math.isclose(
                float(row["meanwhile_improvement"]),
                prior[key] - float(row["error"]), rel_tol=1e-9, abs_tol=1e-6
            )
            or float(row["error"]) > prior[key] + 1e-7
        ):
            raise ValueError(f"100k trial's numerical evidence conflicts with 10k: {key}")
        observed[key] = row
    if set(observed) != expected or len(trials) != 120:
        raise ValueError("20-seed 100k continuation is incomplete")

    trajectories = defaultdict(list)
    for row in history:
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key not in expected:
            raise ValueError(f"unknown trial convergence history: {key}")
        if (
            int(row["seed"]) != int(observed.get(key, {}).get("seed", -1))
            or int(row["dimension"]) != 30
            or not math.isfinite(float(row["best_error"]))
        ):
            raise ValueError(f"invalid history seed/dimension/error: {key}")
        trajectories[key].append(row)
    if set(trajectories) != expected:
        raise ValueError("history is missing at least one algorithm trajectory")
    for key, data in trajectories.items():
        ordered = sorted(data, key=lambda x: int(x["evaluations"]))
        steps = [int(x["evaluations"]) for x in ordered]
        gaps = [float(x["best_error"]) for x in ordered]
        if (
            steps[0] != 100 or steps[-1] != BUDGET
            or len(steps) != len(set(steps))
            or steps.count(10000) != 1
            or any(gap < 0 for gap in gaps)
            or any(y > x + 1e-7 for x, y in pairwise(gaps))
        ):
            raise ValueError(f"incomplete or nonmonotonic trajectory: {key}")
        i = steps.index(10000)
        if (
            not math.isclose(gaps[i], prior[key], rel_tol=1e-9, abs_tol=1e-6)
            or not math.isclose(
                gaps[-1], float(observed[key]["error"]), rel_tol=1e-9, abs_tol=1e-6
            )
        ):
            raise ValueError(f"trajectory mismatch with original records: {key}")
    return trials, history, manifests


def analyse(trials: list[dict]) -> tuple[list[dict], list[dict]]:
    index = {
        (int(t["function_id"]), int(t["repeat"]), t["method"]): t for t in trials
    }
    if len(index) != len(trials) or len(index) != 120:
        raise ValueError("120 unique paired trials are required for statistics")
    summaries, comparisons = [], []
    for fid in FUNCTIONS:
        rng = np.random.default_rng(BOOTSTRAP_SEED + fid)
        indices = rng.integers(0, REPEATS, size=(BOOTSTRAP_REPS, REPEATS))
        values = {}
        for method in METHODS:
            cohort = [index[(fid, i, method)] for i in range(REPEATS)]
            ten = np.asarray([float(t["baseline_10k_error"]) for t in cohort])
            hundred = np.asarray([float(t["error"]) for t in cohort])
            values[method] = hundred
            boot = hundred[indices].mean(axis=1)
            ci = np.quantile(boot, [0.025, 0.975])
            summaries.append({
                "function_id": fid, "method": method, "repeats": REPEATS,
                "mean_error_10k": float(ten.mean()),
                "mean_error_100k": float(hundred.mean()),
                "median_error_100k": float(np.median(hundred)),
                "std_error_100k": float(hundred.std(ddof=1)),
                "bootstrap_mean_error_ci95_low": float(ci[0]),
                "bootstrap_mean_error_ci95_high": float(ci[1]),
                "relative_improvement_pct": float(
                    100 * (1 - hundred.mean() / ten.mean())
                ),
                "mean_elapsed_seconds": statistics.fmean(
                    float(t["elapsed_seconds"]) for t in cohort
                ),
            })
        for other in ("edbf", "re"):
            a, b = values["abc"], values[other]
            wins = int(np.count_nonzero(a < b - 1e-10))
            losses = int(np.count_nonzero(a > b + 1e-10))
            ties = REPEATS - wins - losses
            delta = np.log1p(b) - np.log1p(a)
            ci = np.quantile(delta[indices].mean(axis=1), [0.025, 0.975])
            comparisons.append({
                "function_id": fid, "contrast": "abc_vs_" + other,
                "abc_wins": wins, "abc_losses": losses, "ties": ties,
                "mean_paired_log1p_advantage": float(delta.mean()),
                "paired_log1p_ci95_low": float(ci[0]),
                "paired_log1p_ci95_high": float(ci[1]),
                "p_sign_two_sided": exact_sign_p(wins, losses),
                "p_sign_holm": 1.0,
            })
    indexed = sorted(
        range(len(comparisons)), key=lambda i: comparisons[i]["p_sign_two_sided"]
    )
    adjusted = 0.0
    for rank, i in enumerate(indexed):
        adjusted = max(
            adjusted, min(1.0, comparisons[i]["p_sign_two_sided"] * (4 - rank))
        )
        comparisons[i]["p_sign_holm"] = adjusted
    return summaries, comparisons


def report(summaries: list[dict], comparisons: list[dict]) -> str:
    lines = [
        "# Adaptive 20-seed matched 10k-to-100k CEC2017 study",
        "",
        "120 actual optimizer trajectories across F16/F22 (D=30), ABC/EDBF/RE, "
        "20 paired seeds (repeats 0–19). Seeds 0–4 are the already published "
        "100k continuations; seeds 5–19 are further continuations of the "
        "**same** previously published 10k holdout cohort.",
        "",
        "**Important:** the extension was designed AFTER inspecting the first "
        "five 100k results, in which F22 RE had a lower observed mean than ABC "
        "but very large seed-to-seed variance. This is an adaptive follow-up "
        "and cannot be presented as an independent preregistered confirmation.",
        "",
        "## Measured budget progression (lower error is better)",
        "",
        "| Function | Method | Mean 10k error | Mean 100k error | 100k bootstrap 95% CI |",
        "|:---|:---|---:|---:|:---|",
    ]
    for row in summaries:
        lines.append(
            f"| F{row['function_id']} | {row['method'].upper()} | "
            f"{row['mean_error_10k']:.5g} | {row['mean_error_100k']:.5g} | "
            f"[{row['bootstrap_mean_error_ci95_low']:.5g}, "
            f"{row['bootstrap_mean_error_ci95_high']:.5g}] |"
        )
    lines.extend([
        "",
        "## Paired exact sign tests (4 prespecified contrasts in this extension)",
        "",
        "| Function | Contrast | ABC W/L/T | Raw p | Holm p |",
        "|:---|:---|---:|---:|---:|",
    ])
    for row in comparisons:
        lines.append(
            f"| F{row['function_id']} | {row['contrast']} | "
            f"{row['abc_wins']}/{row['abc_losses']}/{row['ties']} | "
            f"{row['p_sign_two_sided']:.6g} | {row['p_sign_holm']:.6g} |"
        )
    lines.extend([
        "",
        "## Scientific boundaries",
        "",
        "- Reusing 20 held-out seed IDs at longer budgets does NOT create a "
        "second independent cohort; matched 10k/100k curves are repeated "
        "measurements of the same deterministic random trajectories.",
        "- Selection of F16 and F22 followed an earlier unstable ranking; "
        "the expanded 20-seed budget analysis followed an observed 5-seed "
        "F22 reversal. All claims are exploratory and adaptive.",
        "- Bootstrap resamples the 20 paired seed indices 10,000 times using "
        "a reproducible fixed seed. Bootstrap CIs are uncertainty estimates.",
        "- Four two-sided sign tests use Holm multiplicity adjustment, but "
        "this family correction does not control all hypotheses explored "
        "across versions or experimental stages.",
        "- Results are on a pinned Python reference-derived CEC2017 backend, "
        "not the official C executable, and only on two functions.",
        "",
        "## Reproducible evidence",
        "",
        "[120 original trial records](trials.csv) · "
        "[Full convergence history](history.csv) · "
        "[Bootstrap means](summary.csv) · [Paired Holm tests](paired_tests.csv) · "
        "[Provenance](environment.json)",
        "",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard-dir", type=Path, required=True)
    parser.add_argument("--prior-100k", type=Path, default=Path(
        "docs/experiments/cec2017-paperbudget-30d-100k-2026-10-18"
    ))
    parser.add_argument("--prior-10k", type=Path, default=Path(
        "docs/experiments/cec2017-holdout-30d-10k-2026-10-17/trials.csv"
    ))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    trials, history, manifests = validate(
        args.shard_dir, args.prior_100k, args.prior_10k
    )
    summaries, comparisons = analyse(trials)
    target = args.output_dir
    trials.sort(key=lambda t: (int(t["function_id"]), int(t["repeat"]), t["method"]))
    history.sort(key=lambda h: (
        int(h["function_id"]), int(h["repeat"]),
        h["method"], int(h["evaluations"])
    ))
    write(target / "trials.csv", trials)
    write(target / "history.csv", history)
    write(target / "summary.csv", summaries)
    write(target / "paired_tests.csv", comparisons)
    env = {
        "functions": list(FUNCTIONS), "methods": list(METHODS),
        "dimension": 30, "repeats": REPEATS, "evaluations": BUDGET,
        "baseline_evaluations": 10000, "base_seed": BASE_SEED,
        "reference_commit": REFERENCE_COMMIT, "trials": len(trials),
        "history_rows": len(history), "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_resamples": BOOTSTRAP_REPS,
        "adaptive_extension": True, "original_5seed_source_run_sha": ORIGINAL_RUN_SHA,
        "source_manifests": manifests, "python": sys.version,
        "numpy": np.__version__, "platform": platform.platform(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (target / "environment.json").write_text(
        json.dumps(env, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (target / "report.md").write_text(report(summaries, comparisons), encoding="utf-8")
    print(
        f"Verified {len(trials)} real matched 100k trials, "
        f"{len(history)} convergence states; inferred 4 Holm-adjusted contrasts."
    )


if __name__ == "__main__":
    main()
