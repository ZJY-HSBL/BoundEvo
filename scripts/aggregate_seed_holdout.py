"""Validate genuinely new paired seeds and quantify F16/F22 uncertainty.

The evaluation seeds 20261037 + F*10000 + repeat (repeat 0..19) are
disjoint from all previously published seed ranges 0..9 at base 20261017.
No fallback results: incomplete function cohorts fail the merger.
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
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from boundevo.cec2017 import REFERENCE_COMMIT, REFERENCE_REPO

FUNCTIONS = (16, 22)
METHODS = ("abc", "edbf", "re")
REPEATS = 20
EVALUATIONS = 10_000
SEED_BASE = 20261037
BOOTSTRAP_SEED = 20261017
BOOTSTRAP_REPETITIONS = 10_000


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError(f"missing experiment file: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("empty experiment CSV")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def validate(input_dir: Path) -> tuple[list[dict], list[dict]]:
    trials: list[dict] = []
    manifests: list[dict] = []
    for fid in FUNCTIONS:
        folder = input_dir / f"f{fid}"
        env_path = folder / "environment.json"
        if not env_path.is_file():
            raise ValueError(f"missing environment manifest for F{fid}")
        env = json.loads(env_path.read_text(encoding="utf-8"))
        expected = {
            "functions": [fid], "dimension": 30, "repeats": REPEATS,
            "evaluations": EVALUATIONS, "base_seed": SEED_BASE,
            "reference_commit": REFERENCE_COMMIT,
        }
        if any(env.get(key) != value for key, value in expected.items()):
            raise ValueError(f"incompatible experiment manifest for F{fid}")
        checks = read_csv(folder / "backend_preflight.csv")
        if len(checks) != 58 or any(check["status"] != "pass" for check in checks):
            raise ValueError(f"failed numerical backend preflight for F{fid}")
        rows = read_csv(folder / "trials.csv")
        if len(rows) != REPEATS * len(METHODS):
            raise ValueError(f"F{fid}: incomplete trial count")
        trials.extend(rows)
        manifests.append(env)
    expected_keys = {(fid, rep, m) for fid in FUNCTIONS
                     for rep in range(REPEATS) for m in METHODS}
    observed = {}
    for row in trials:
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key not in expected_keys or key in observed:
            raise ValueError(f"unknown or duplicate trial {key}")
        fid, rep, _ = key
        if (
            int(row["seed"]) != SEED_BASE + fid * 10_000 + rep
            or int(row["dimension"]) != 30
            or int(row["evaluations"]) != EVALUATIONS
            or int(row["generations"]) < 1
        ):
            raise ValueError(f"wrong seed, dimension or evaluation budget: {key}")
        for numeric in (
            "objective", "optimum", "error", "elapsed_seconds",
            "attempts_per_offspring",
        ):
            if not math.isfinite(float(row[numeric])):
                raise ValueError(f"invalid {numeric} in {key}")
        gap = float(row["objective"]) - float(row["optimum"])
        if gap < -1e-6 or not math.isclose(float(row["error"]), gap, abs_tol=1e-6):
            raise ValueError(f"objective/known-optimum mismatch: {key}")
        if float(row["attempts_per_offspring"]) < 1:
            raise ValueError(f"invalid number of coefficient proposals in {key}")
        observed[key] = row
    if set(observed) != expected_keys:
        raise ValueError("incomplete paired experiment")
    return trials, manifests


def exact_sign_p(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(k + 1)) / 2**n)


def summarize(trials: list[dict]) -> tuple[list[dict], list[dict]]:
    lookup = {
        (int(row["function_id"]), int(row["repeat"]), row["method"]): row
        for row in trials
    }
    summary = []
    comparisons = []
    for fid in FUNCTIONS:
        rng = np.random.default_rng(BOOTSTRAP_SEED + fid)
        indices = rng.integers(0, REPEATS, size=(BOOTSTRAP_REPETITIONS, REPEATS))
        errors = {
            method: np.array(
                [float(lookup[(fid, rep, method)]["error"]) for rep in range(REPEATS)]
            )
            for method in METHODS
        }
        for method in METHODS:
            values = errors[method]
            bootstrap_means = values[indices].mean(axis=1)
            lower, upper = np.quantile(bootstrap_means, [0.025, 0.975])
            records = [lookup[(fid, rep, method)] for rep in range(REPEATS)]
            summary.append(
                {
                    "function_id": fid, "method": method, "repeats": REPEATS,
                    "mean_error": statistics.fmean(values.tolist()),
                    "std_error": statistics.stdev(values.tolist()),
                    "median_error": statistics.median(values.tolist()),
                    "bootstrap_mean_error_ci95_low": float(lower),
                    "bootstrap_mean_error_ci95_high": float(upper),
                    "mean_elapsed_seconds": statistics.fmean(
                        float(row["elapsed_seconds"]) for row in records
                    ),
                    "mean_attempts_per_offspring": statistics.fmean(
                        float(row["attempts_per_offspring"]) for row in records
                    ),
                    "mean_evaluations": statistics.fmean(
                        float(row["evaluations"]) for row in records
                    ),
                }
            )
        for baseline in ("edbf", "re"):
            a = errors["abc"]
            b = errors[baseline]
            wins = int(np.count_nonzero(a < b - 1e-10))
            losses = int(np.count_nonzero(a > b + 1e-10))
            ties = REPEATS - wins - losses
            # Paired log1p gap retains the same seed in each resample;
            # positive values favour ABC. Bootstrap measures uncertainty.
            delta = np.log1p(b) - np.log1p(a)
            distribution = delta[indices].mean(axis=1)
            lo, hi = np.quantile(distribution, [0.025, 0.975])
            comparisons.append(
                {
                    "function_id": fid, "comparison": "abc_vs_" + baseline,
                    "abc_wins": wins, "abc_losses": losses, "ties": ties,
                    "mean_paired_log1p_advantage": float(delta.mean()),
                    "paired_log1p_ci95_low": float(lo),
                    "paired_log1p_ci95_high": float(hi),
                    "p_sign_two_sided": exact_sign_p(wins, losses),
                    "p_sign_holm": 1.0,
                }
            )
    ordered = sorted(range(len(comparisons)), key=lambda i: comparisons[i]["p_sign_two_sided"])
    adjusted = 0.0
    for rank, idx in enumerate(ordered):
        adjusted = max(
            adjusted,
            min(1.0, comparisons[idx]["p_sign_two_sided"] * (len(comparisons) - rank)),
        )
        comparisons[idx]["p_sign_holm"] = adjusted
    return summary, comparisons


def report(summary: list[dict], comparisons: list[dict]) -> str:
    index = {(int(r["function_id"]), r["method"]): r for r in summary}
    lines = [
        "# Independent fresh-seed holdout: CEC2017 F16 and F22",
        "",
        "## Protocol",
        "",
        "- D=30, 10,000 function evaluations including N=100 initialization.",
        "- F16 and F22, three methods ABC/EDBF/RE.",
        "- Twenty **new** independent seeds per method/function: "
        "20261037 + 10,000 × function ID + repeat, repeat 0..19.",
        "- The seed range is disjoint from the previously published seeds "
        "at base 20261017 with repeat IDs 0..9.",
        "- 120 measured optimization trials. Matched initialization within each repeat.",
        "- Benchmark backend: independent C-derived Python port at revision "
        + REFERENCE_COMMIT + ".",
        "- Confidence intervals: 10,000 paired bootstrap resamples, fixed seed "
        "20261017 + function ID, percentile 95% intervals.",
        "- Exact two-sided paired sign tests; Holm correction over four contrasts.",
        "",
        "## Measured means with percentile bootstrap 95% CI",
        "",
        "| Function | Method | Mean objective error | 95% CI for mean error |",
        "|:---|:---|---:|:---|",
    ]
    for fid in FUNCTIONS:
        for method in METHODS:
            row = index[(fid, method)]
            lines.append(
                f"| F{fid} | {method.upper()} | {row['mean_error']:.6g} | "
                f"[{row['bootstrap_mean_error_ci95_low']:.6g}, "
                f"{row['bootstrap_mean_error_ci95_high']:.6g}] |"
            )
    lines += [
        "",
        "## Matched comparisons (ABC versus baselines)",
        "",
        "| Function | Contrast | ABC W/L/T | Raw p | Holm p | Paired log1p difference (95% CI) |",
        "|:---|:---|---:|---:|---:|:---|",
    ]
    for row in comparisons:
        lines.append(
            f"| F{row['function_id']} | {row['comparison']} | "
            f"{row['abc_wins']}/{row['abc_losses']}/{row['ties']} | "
            f"{row['p_sign_two_sided']:.6g} | {row['p_sign_holm']:.6g} | "
            f"{row['mean_paired_log1p_advantage']:+.5g} "
            f"[{row['paired_log1p_ci95_low']:+.5g}, "
            f"{row['paired_log1p_ci95_high']:+.5g}] |"
        )
    lines += [
        "",
        "## Interpretation limits",
        "",
        "- This is a **holdout** cohort chosen after prior F16/F22 sensitivity "
        "was detected; the listed seeds themselves were not included in the "
        "prior experiments.",
        "- Bootstrap confidence intervals use ordinary empirical resampling "
        "of 20 matched seed indices; they are estimates, not exact coverage guarantees.",
        "- The sign test conditions on non-tied pairs; Holm controls the tested "
        "four-contrast family, not every benchmark hypothesis considered previously.",
        "- The paired log1p advantage is positive if ABC tends to produce "
        "smaller objective gaps on the same seeds.",
        "- F16/F22 were selected for ambiguity. These results cannot establish "
        "general optimization superiority across all CEC2017 functions.",
        "- Running times depend on the Python implementation and GitHub runner.",
        "- The fixed reference-derived Python CEC2017 implementation is not "
        "the organizers' original C binary.",
        "",
        "## Source data",
        "",
        "[120 measured trial rows](trials.csv) · "
        "[method-level summary and bootstrap CI](summary.csv) · "
        "[Holm-adjusted paired comparisons](paired_tests.csv) · "
        "[runtime provenance](environment.json)",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    trials, manifests = validate(args.input_dir)
    summary, comparisons = summarize(trials)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    trials.sort(key=lambda row: (
        int(row["function_id"]), int(row["repeat"]), row["method"]
    ))
    write_csv(output / "trials.csv", trials)
    write_csv(output / "summary.csv", summary)
    write_csv(output / "paired_tests.csv", comparisons)
    environment = {
        "functions": list(FUNCTIONS), "methods": list(METHODS),
        "dimension": 30, "repeats": REPEATS, "evaluations": EVALUATIONS,
        "seed_base": SEED_BASE, "reference_commit": REFERENCE_COMMIT,
        "reference_repo": REFERENCE_REPO, "trials": len(trials),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_resamples": BOOTSTRAP_REPETITIONS,
        "source_job_commits": [row.get("git_sha") for row in manifests],
        "python": sys.version, "numpy": np.__version__,
        "platform": platform.platform(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output / "environment.json").write_text(
        json.dumps(environment, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "report.md").write_text(
        report(summary, comparisons), encoding="utf-8"
    )
    print(
        f"Verified {len(trials)} strictly paired holdout trial rows. "
        f"Mean error leaders: "
        f"{ {fid: min(METHODS, key=lambda m: next(float(r['mean_error']) for r in summary if r['function_id']==fid and r['method']==m)) for fid in FUNCTIONS} }",
        flush=True,
    )


if __name__ == "__main__":
    main()
