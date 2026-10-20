"""Validate the ABC coefficient-order experiment and publish paired scientific evidence."""

from __future__ import annotations

# ruff: noqa: ISC004

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

FUNCTIONS = (10, 16, 20, 22)
METHODS = ("abc", "abc_shuffle")
REPEATS = 10
BASE_SEED = 20261121
BUDGET = 10_000


def read(filename: Path) -> list[dict]:
    if not filename.is_file():
        raise ValueError(f"missing actual experiment file: {filename}")
    with filename.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"empty original experiment: {filename}")
    return rows


def write(filename: Path, records: list[dict]) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        raise ValueError("cannot publish an empty scientific table")
    with filename.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def sign_test(wins: int, losses: int) -> float:
    n = wins+losses
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(wins, losses)+1))/2**n)


def verify(source: Path) -> tuple[list[dict], list[dict], list[dict]]:
    trials, history, sources = [], [], []
    for fid in FUNCTIONS:
        directory = source / f"f{fid}"
        env = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        expected = {
            "function_id": fid, "methods": list(METHODS), "dimension": 30,
            "repeats": REPEATS, "evaluations": BUDGET, "base_seed": BASE_SEED,
            "history_interval": 450, "reference_commit": REFERENCE_COMMIT,
        }
        if any(env.get(k) != v for k, v in expected.items()) or not env.get("source_commit"):
            raise ValueError(f"invalid frozen provenance in F{fid}")
        t = read(directory / "trials.csv")
        if len(t) != REPEATS*len(METHODS):
            raise ValueError(f"incomplete real trials in F{fid}")
        trials.extend(t)
        history.extend(read(directory / "history.csv"))
        sources.append(env)
    expected_keys = {(fid, seed, method)
                     for fid in FUNCTIONS for seed in range(REPEATS) for method in METHODS}
    observed = {}
    for row in trials:
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key not in expected_keys or key in observed:
            raise ValueError(f"duplicate/unexpected raw seed {key}")
        fid, rep, _ = key
        if (int(row["evaluations"]) != BUDGET or int(row["dimension"]) != 30
                or int(row["seed"]) != BASE_SEED + fid*10000+rep):
            raise ValueError(f"wrong budget / matched seed {key}")
        if any(not math.isfinite(float(row[x]))
               for x in ("objective", "optimum", "error", "elapsed_seconds")):
            raise ValueError(f"nonfinite result {key}")
        if not math.isclose(
            float(row["objective"])-float(row["optimum"]),
            float(row["error"]), abs_tol=1e-6, rel_tol=1e-10
        ) or float(row["error"]) < 0:
            raise ValueError(f"reported optimum / error inconsistent {key}")
        observed[key] = row
    if set(observed) != expected_keys or len(trials) != 80:
        raise ValueError("the ablation requires 80 independently executed trials")
    grouped = defaultdict(list)
    for row in history:
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key not in expected_keys or not math.isfinite(float(row["best_error"])):
            raise ValueError(f"invalid original history {key}")
        grouped[key].append(row)
    if set(grouped) != expected_keys:
        raise ValueError("missing convergence histories")
    for key, points in grouped.items():
        points.sort(key=lambda x: int(x["evaluations"]))
        steps = [int(x["evaluations"]) for x in points]
        errs = [float(x["best_error"]) for x in points]
        if (steps[0] != 100 or steps[-1] != BUDGET
                or len(steps) != len(set(steps))
                or any(a < b-1e-7 for a, b in pairwise(errs))
                or not math.isclose(errs[-1], float(observed[key]["error"]), abs_tol=1e-6)
                or any(int(x["seed"]) != int(observed[key]["seed"]) for x in points)):
            raise ValueError(f"invalid original optimizer checkpoint {key}")
    for fid in FUNCTIONS:
        for rep in range(REPEATS):
            start = [float(grouped[(fid, rep, m)][0]["best_error"]) for m in METHODS]
            if not math.isclose(start[0], start[1], abs_tol=1e-8, rel_tol=1e-12):
                raise ValueError(f"mismatched paired initial population F{fid} seed {rep}")
    trials.sort(key=lambda x: (int(x["function_id"]), int(x["repeat"]), x["method"]))
    history.sort(key=lambda x: (
        int(x["function_id"]), int(x["repeat"]), x["method"], int(x["evaluations"])
    ))
    return trials, history, sources


def analyse(trials: list[dict]) -> tuple[list[dict], list[dict], dict]:
    indexed = {(int(t["function_id"]), int(t["repeat"]), t["method"]): t for t in trials}
    if len(indexed) != 80:
        raise ValueError("missing matched records")
    summary, comparisons, deltas = [], [], {}
    for fid in FUNCTIONS:
        rng = np.random.default_rng(BASE_SEED+fid)
        draw = rng.integers(0, REPEATS, size=(10_000, REPEATS))
        error = {}
        for method in METHODS:
            vals = np.asarray([float(indexed[(fid, i, method)]["error"]) for i in range(REPEATS)])
            error[method] = vals
            ci = np.quantile(vals[draw].mean(axis=1), [0.025, 0.975])
            summary.append({
                "function_id": fid, "method": method, "repeats": REPEATS,
                "mean_error": float(vals.mean()),
                "median_error": float(np.median(vals)),
                "std_error": float(vals.std(ddof=1)),
                "bootstrap_mean_ci95_low": float(ci[0]),
                "bootstrap_mean_ci95_high": float(ci[1]),
                "mean_elapsed_seconds": float(np.mean([
                    float(indexed[(fid, i, method)]["elapsed_seconds"]) for i in range(REPEATS)
                ])),
            })
        delta = np.log1p(error["abc"])-np.log1p(error["abc_shuffle"])
        # Positive = shuffled ABC has lower error than unshuffled ABC.
        deltas[fid] = [float(v) for v in delta]
        wins = int(np.count_nonzero(delta > 1e-10))
        losses = int(np.count_nonzero(delta < -1e-10))
        ci = np.quantile(delta[draw].mean(axis=1), [0.025, 0.975])
        comparisons.append({
            "function_id": fid, "shuffled_wins": wins, "shuffled_losses": losses,
            "ties": REPEATS-wins-losses,
            "mean_paired_log1p_gain": float(delta.mean()),
            "bootstrap_paired_ci95_low": float(ci[0]),
            "bootstrap_paired_ci95_high": float(ci[1]),
            "exact_sign_p": sign_test(wins, losses), "holm_sign_p": 1.0,
        })
    previous = 0.0
    for rank, i in enumerate(sorted(range(4), key=lambda i: comparisons[i]["exact_sign_p"])):
        previous = max(previous, min(1.0, comparisons[i]["exact_sign_p"] * (4-rank)))
        comparisons[i]["holm_sign_p"] = previous
    return summary, comparisons, deltas


def render_svg(tests: list[dict], deltas: dict) -> str:
    from html import escape
    colors = ("#136392", "#d4842a", "#2b8a73", "#a35e92")
    largest = max(0.1, max(abs(x) for values in deltas.values() for x in values) * 1.10)
    x0, width = 310, 690
    pos = lambda value: x0 + width * (value+largest) / (2*largest)
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1190" height="655" viewBox="0 0 1190 655">',
        '<rect width="1190" height="655" fill="#f8fafc"/>',
        '<text x="64" y="55" font-size="27" fill="#14263e" font-family="Arial" font-weight="700">'
        'ABC coefficient-order ablation | Per-seed effects</text>',
        '<text x="64" y="85" font-size="15" fill="#64748b" font-family="Arial">'
        'F10/F16/F20/F22 · 30D · 10 new paired seeds · 10k FE · positive favors ABC-Shuffle</text>',
        f'<line x1="{pos(0):.1f}" y1="150" x2="{pos(0):.1f}" y2="562" '
        'stroke="#475569" stroke-dasharray="5 5" stroke-width="2"/>',
    ]
    for idx, r in enumerate(tests):
        fid = int(r["function_id"])
        y = 192 + idx*98
        out.append(f'<rect x="61" y="{y-49}" width="1060" height="89" rx="9" '
                   'fill="white" stroke="#e4eaf1"/>')
        out.append(f'<text x="83" y="{y-4}" font-size="20" fill="#1e293b" '
                   f'font-family="Arial" font-weight="700">F{fid}</text>')
        out.append(f'<text x="83" y="{y+20}" font-size="13" fill="#64748b" '
                   f'font-family="Arial">Shuffle W/L {r["shuffled_wins"]}/{r["shuffled_losses"]}</text>')
        out.append(f'<line x1="{pos(0):.1f}" y1="{y-28}" x2="{pos(0):.1f}" y2="{y+28}" '
                   'stroke="#94a3b8" stroke-dasharray="5 5"/>')
        for seed, effect in enumerate(deltas[fid]):
            x = pos(effect)
            offset = ((seed % 5)-2)*7.5
            out.append(f'<circle cx="{x:.2f}" cy="{y+offset:.1f}" r="6" '
                       f'fill="{colors[idx]}" fill-opacity="0.78" stroke="white"/>')
        mean = float(r["mean_paired_log1p_gain"])
        lo, hi = float(r["bootstrap_paired_ci95_low"]), float(r["bootstrap_paired_ci95_high"])
        out.append(f'<line x1="{pos(lo):.2f}" y1="{y+28}" x2="{pos(hi):.2f}" y2="{y+28}" '
                   'stroke="#111827" stroke-width="4"/>')
        out.append(f'<circle cx="{pos(mean):.2f}" cy="{y+28}" r="5" fill="#111827"/>')
        out.append(f'<text x="1013" y="{y+2}" font-size="13" fill="#334155" '
                   f'font-family="Arial">{escape(f"p={float(r["holm_sign_p"]):.3g}")}</text>')
    for value in (-largest, 0, largest):
        out.append(f'<text x="{pos(value):.2f}" y="605" font-size="13" '
                   f'text-anchor="middle" font-family="Arial" fill="#475569">{value:+.2f}</text>')
    out.append('<text x="62" y="641" font-size="12" font-family="Arial" fill="#64748b">'
               'Dots: individual seed log1p gains; black bars: 95% paired bootstrap intervals; '
               'sign tests Holm-adjusted across four functions.</text>')
    out.append('</svg>')
    return "\n".join(out)+"\n"


def report(summary: list[dict], comparisons: list[dict]) -> str:
    out = [
        "# ABC-Shuffle: coefficient order / elite-rank coupling ablation",
        "",
        ("Original ABC generates an ordered vector of constrained affine weights. "
         "The optimizer supplies elite-first ordered parents. ABC-Shuffle generates "
         "the same valid coefficient multiset, then permutes it before the "
         "offspring construction; this removes deterministic coefficient index "
         "alignment without changing the coefficients themselves."),
        "",
        "**Mechanistic exploratory experiment, not a claim of algorithmic novelty.** "
        "F10/F16/F20/F22, D=30, 10,000 FEs, 10 new paired seeds, two methods, "
        "**80 real optimization trials**. Initial populations and budgets are identical. "
        "Extra permutation RNG use changes subsequent randomness; this is not a "
        "common-random-number coupling at every later generation.",
        "",
        "## Mean objective error (lower is better)",
        "",
        "| Function | ABC | ABC-Shuffle |", "|:---|---:|---:|",
    ]
    indexed = {(int(r["function_id"]), r["method"]): r for r in summary}
    for fid in FUNCTIONS:
        out.append(
            f"| F{fid} | {float(indexed[(fid, 'abc')]['mean_error']):.6g} | "
            f"{float(indexed[(fid, 'abc_shuffle')]['mean_error']):.6g} |"
        )
    out.extend(["", "## Matched-seed paired tests", "",
                "| Function | Shuffle W/L/T | paired log1p gain | bootstrap 95% CI | Holm p |",
                "|:---|---:|---:|:---|---:|"])
    for r in comparisons:
        out.append(
            f"| F{r['function_id']} | {r['shuffled_wins']}/{r['shuffled_losses']}/{r['ties']} | "
            f"{r['mean_paired_log1p_gain']:+.5f} | "
            f"[{r['bootstrap_paired_ci95_low']:+.5f}, "
            f"{r['bootstrap_paired_ci95_high']:+.5f}] | {r['holm_sign_p']:.6g} |"
        )
    out.extend([
        "", "The positive paired log1p gain indicates that ABC-Shuffle has lower "
        "error in that seed. Rejection-free feasibility and the coefficient "
        "multiset are preserved; a single factor (coefficient position) is changed. "
        "All conclusions are exploratory because the functions were selected after "
        "earlier research and this is a small, 10-seed cohort.",
        "", "[80 original trials](trials.csv) · [original convergence history](history.csv) · "
        "[summary and intervals](summary.csv) · [paired tests](paired_tests.csv) · "
        "[manifest](environment.json)", "",
    ])
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--figure", required=True, type=Path)
    args = p.parse_args()
    trials, history, sources = verify(args.input_dir)
    summary, comparisons, deltas = analyse(trials)
    write(args.output_dir/"trials.csv", trials)
    write(args.output_dir/"history.csv", history)
    write(args.output_dir/"summary.csv", summary)
    write(args.output_dir/"paired_tests.csv", comparisons)
    manifest = {
        "functions": list(FUNCTIONS), "methods": list(METHODS), "repeats": REPEATS,
        "evaluations": BUDGET, "dimension": 30, "trials": len(trials),
        "history_rows": len(history), "base_seed": BASE_SEED,
        "reference_commit": REFERENCE_COMMIT, "bootstrap_resamples": 10_000,
        "study_type": "exploratory coefficient-rank decoupling ablation",
        "source_manifests": sources,
        "python": sys.version, "numpy": np.__version__,
        "platform": platform.platform(), "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (args.output_dir/"environment.json").write_text(
        json.dumps(manifest, indent=2)+"\n", encoding="utf-8"
    )
    (args.output_dir/"report.md").write_text(report(summary, comparisons), encoding="utf-8")
    args.figure.parent.mkdir(parents=True, exist_ok=True)
    args.figure.write_text(render_svg(comparisons, deltas), encoding="utf-8")
    print(f"Validated {len(trials)} original optimizer runs, "
          f"{len(history)} actual checkpoints and four Holm-adjusted paired tests.")


if __name__ == "__main__":
    main()
