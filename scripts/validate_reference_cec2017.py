"""Independent 30D CEC2017 validation with a pinned reference-derived backend.

Per-function/per-repeat seeds are identical across ABC, EDBF, and RE.
No fabricated data, zero-clipped negative gaps, or fallback benchmark values.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import statistics
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np

from boundevo.cec2017 import (
    PAPER_FUNCTION_IDS,
    REFERENCE_COMMIT,
    REFERENCE_REPO,
    make_cec2017_case,
)
from boundevo.experiments import paper_config, run_case


def package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def csv_output(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("empty output")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def preflight(dimensions: list[int], seed: int) -> list[dict]:
    """Probe all official F1,F3..F30 with zeros and five uniform random points."""

    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    for dimension in dimensions:
        for fid in PAPER_FUNCTION_IDS:
            case = make_cec2017_case(fid, dimension, backend="reference")
            probes = np.vstack(
                (np.zeros((1, dimension)), rng.uniform(-100, 100, size=(5, dimension)))
            )
            observed = []
            status = "pass"
            detail = ""
            for point in probes:
                try:
                    val = case.problem.evaluate(point).objective
                    observed.append(val)
                    if val < case.optimum - max(1e-7, case.optimum * 1e-9):
                        status, detail = "fail", "objective below declared optimum"
                        break
                except (ValueError, FloatingPointError, RuntimeError) as exc:
                    status, detail = "fail", str(exc)
                    break
            rows.append(
                {
                    "dimension": dimension,
                    "function_id": fid,
                    "status": status,
                    "detail": detail,
                    "optimum": case.optimum,
                    "minimum_probe_value": min(observed) if observed else "",
                    "probes_completed": len(observed),
                }
            )
            print(
                f"PRECHECK D={dimension} F{fid} status={status} "
                f"min={min(observed) if observed else 'NA'}",
                flush=True,
            )
    return rows


def summarize(trials: list[dict]) -> list[dict]:
    grouped: dict[tuple[int, str], list[dict]] = {}
    for trial in trials:
        grouped.setdefault((trial["function_id"], trial["method"]), []).append(trial)
    result = []
    for (fid, method), items in sorted(grouped.items()):
        result.append(
            {
                "function_id": fid,
                "method": method,
                "repeats": len(items),
                "mean_error": statistics.fmean(item["error"] for item in items),
                "std_error": statistics.stdev(item["error"] for item in items),
                "median_error": statistics.median(item["error"] for item in items),
                "mean_elapsed_seconds": statistics.fmean(
                    item["elapsed_seconds"] for item in items
                ),
                "mean_evaluations": statistics.fmean(item["evaluations"] for item in items),
                "mean_attempts_per_offspring": statistics.fmean(
                    item["attempts_per_offspring"] for item in items
                ),
            }
        )
    return result


def two_sided_exact_sign_p(differences: list[float]) -> float:
    """Exact two-sided sign test, omitting numerical ties."""

    nonzero = [value for value in differences if abs(value) > 1e-10]
    n = len(nonzero)
    if n == 0:
        return 1.0
    k = min(sum(value > 0 for value in nonzero), sum(value < 0 for value in nonzero))
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(k + 1)) / 2**n)


def comparisons(trials: list[dict], funcs: list[int], repeats: int) -> list[dict]:
    index = {(row["function_id"], row["repeat"], row["method"]): row for row in trials}
    out = []
    for fid in funcs:
        for opponent in ("edbf", "re"):
            differences = [
                index[(fid, rep, opponent)]["error"] - index[(fid, rep, "abc")]["error"]
                for rep in range(repeats)
            ]
            out.append(
                {
                    "function_id": fid,
                    "comparison": f"abc_vs_{opponent}",
                    "abc_wins": sum(delta > 1e-10 for delta in differences),
                    "ties": sum(abs(delta) <= 1e-10 for delta in differences),
                    "abc_losses": sum(delta < -1e-10 for delta in differences),
                    "p_sign_two_sided": two_sided_exact_sign_p(differences),
                    "mean_opponent_minus_abc_error": statistics.fmean(differences),
                }
            )
    return out


def report_text(config: dict, rows: list[dict], tests: list[dict], checks: list[dict]) -> str:
    lines = [
        "# BoundEvo: independent-reference 30D CEC2017 comparison",
        "",
        ("This document reports measured numbers from GitHub Actions. It is not "
        "a complete reproduction of the source paper."),
        "",
        f"Reference-derived implementation: {REFERENCE_REPO}",
        f"Pinned upstream commit: {REFERENCE_COMMIT}",
        "",
        "## Protocol",
        "",
        f"- Dimensions: {config['dimension']}.",
        f"- Functions: {config['functions']}.",
        f"- Methods: ABC, EDBF, RE; repeats per function: {config['repeats']}.",
        f"- Evaluation budget per trial, including initial population: {config['evaluations']}.",
        "- N=100, M=15, K=5, L=1; bounded offspring repaired by clipping.",
        "- Identical seed and initial population for the three methods within each pair.",
        "- Strict objective gap check; no negative error gap is silently truncated.",
        "- Preflight: 29 official functions in 10D and 30D; zero + 5 random points each.",
        "",
        "## Numerical integrity preflight",
        "",
        f"- Cases tested: {len(checks)}; passed: {sum(r['status']=='pass' for r in checks)}.",
        "",
        "## Mean objective error (lower is better)",
        "",
        "| Function | ABC | EDBF | RE |",
        "|:---|---:|---:|---:|",
    ]
    lookup = {(item["function_id"], item["method"]): item for item in rows}
    for fid in config["functions"]:
        lines.append(
            "| F{} | {:.6g} | {:.6g} | {:.6g} |".format(
                fid,
                lookup[(fid, "abc")]["mean_error"],
                lookup[(fid, "edbf")]["mean_error"],
                lookup[(fid, "re")]["mean_error"],
            )
        )
    lines.extend(
        [
            "",
            "## Paired exact sign tests (exploratory)",
            "",
            "| Function | Contrast | ABC wins | Ties | ABC losses | Two-sided p |",
            "|:---|:---|---:|---:|---:|---:|",
        ]
    )
    for row in tests:
        lines.append(
            f"| F{row['function_id']} | {row['comparison']} | "
            f"{row['abc_wins']} | {row['ties']} | {row['abc_losses']} | "
            f"{row['p_sign_two_sided']:.6g} |"
        )
    lines += [
        "",
        ("The sign tests are per-function and exploratory; multiple comparisons "
        "are not corrected here. Do not interpret these p values as a "
        "family-wise significant result."),
        "",
        "## Timing and generator efficiency",
        "",
        "| Function | Method | Mean runtime (s) | Coefficient proposals per child |",
        "|:---|:---|---:|---:|",
    ]
    for fid in config["functions"]:
        for method in ("abc", "edbf", "re"):
            item = lookup[(fid, method)]
            lines.append(
                f"| F{fid} | {method} | {item['mean_elapsed_seconds']:.3f} | "
                f"{item['mean_attempts_per_offspring']:.3f} |"
            )
    lines += [
        "",
        "## Limitations",
        "",
        ("- A pinned C-derived Python implementation is an independent cross-check, "
        "not byte-for-byte execution of the organizers' official C binaries."),
        "- Small numbers of functions and repetitions cannot establish general superiority.",
        "- Equal evaluation budgets do not equalize implementation overhead.",
        "- Shared random seeds equalize initial populations, not later RNG streams.",
        ("- Differences from the opfunu pilot reflect a change of benchmark backend; "
        "the numeric values from different backends must not be pooled."),
        ("- More repetitions, validated complete 29-function coverage, and "
        "paper-matching stopping rules are needed for publication claims."),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--functions", type=int, nargs="+", default=[1, 3, 10, 30])
    parser.add_argument("--dimensions-preflight", type=int, nargs="+", default=[10, 30])
    parser.add_argument("--dimension", type=int, default=30)
    parser.add_argument("--methods", nargs="+", default=["abc", "edbf", "re"])
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--evaluations", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=20261017)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/experiments/cec2017-reference-30d-2026-10-17"),
    )
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if set(args.methods) != {"abc", "edbf", "re"} or len(args.methods) != 3:
        parser.error("all three unique methods abc edbf re are required")
    if args.repeats < 2 or args.evaluations < 100:
        parser.error("repeats >= 2 and evaluations >= 100 are required")
    target = args.output_dir
    target.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    checks = preflight(args.dimensions_preflight, args.seed)
    csv_output(target / "backend_preflight.csv", checks)
    passed = {
        (row["dimension"], row["function_id"])
        for row in checks
        if row["status"] == "pass"
    }
    selected = {(args.dimension, fid) for fid in args.functions}
    if not selected.issubset(passed):
        raise RuntimeError(
            f"reference backend failed preflight for requested cases: {selected - passed}"
        )
    if args.preflight_only:
        print(f"Preflight: {len(passed)}/{len(checks)} passed")
        return

    trials: list[dict] = []
    for fid in args.functions:
        case = make_cec2017_case(fid, args.dimension, backend="reference")
        for rep in range(args.repeats):
            seed = args.seed + fid * 10000 + rep
            for method in args.methods:
                result = run_case(
                    case,
                    method=method,
                    repeat=rep,
                    seed=seed,
                    config=paper_config(
                        method=method,
                        max_evaluations=args.evaluations,
                        seed=seed,
                    ),
                    history_interval=250,
                )
                if result.evaluations != args.evaluations:
                    raise RuntimeError(
                        f"unexpected early convergence on F{fid} rep={rep}: "
                        f"{result.evaluations} rather than {args.evaluations}"
                    )
                row = asdict(result)
                row["attempts_per_offspring"] = (
                    result.coefficient_attempts / (result.evaluations - 100)
                )
                trials.append(row)
                print(
                    f"F{fid} D={args.dimension} rep={rep} {method}: "
                    f"error={result.error:.8g} elapsed={result.elapsed_seconds:.2f}s "
                    f"attempts/child={row['attempts_per_offspring']:.2f}",
                    flush=True,
                )

    expected = len(args.functions) * args.repeats * 3
    if len(trials) != expected:
        raise RuntimeError(f"expected {expected} trials, got {len(trials)}")
    output_summary = summarize(trials)
    paired_tests = comparisons(trials, args.functions, args.repeats)
    csv_output(target / "trials.csv", trials)
    csv_output(target / "summary.csv", output_summary)
    csv_output(target / "paired_sign_tests.csv", paired_tests)
    config = {
        "functions": args.functions,
        "dimension": args.dimension,
        "repeats": args.repeats,
        "evaluations": args.evaluations,
        "base_seed": args.seed,
        "reference_repo": REFERENCE_REPO,
        "reference_commit": REFERENCE_COMMIT,
        "git_sha": os.environ.get("GITHUB_SHA"),
        "python_version": sys.version,
        "platform": platform.platform(),
        "numpy_version": package_version("numpy"),
        "cec2017_version": package_version("CEC2017"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": time.perf_counter() - start,
        "preflight_passed": sum(row["status"] == "pass" for row in checks),
        "preflight_total": len(checks),
    }
    (target / "environment.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (target / "report.md").write_text(
        report_text(config, output_summary, paired_tests, checks), encoding="utf-8"
    )
    print(f"Saved {len(trials)} trials to {target}.", flush=True)


if __name__ == "__main__":
    main()
