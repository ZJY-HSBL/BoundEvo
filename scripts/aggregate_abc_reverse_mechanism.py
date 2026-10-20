"""Three-arm matched-seed ABC positional-bias audit and real optimization evidence."""

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
from html import escape
from itertools import pairwise
from pathlib import Path
from xml.etree import ElementTree

import numpy as np

from boundevo.cec2017 import REFERENCE_COMMIT
from boundevo.coefficients import adaptive_boundary_coefficients, is_valid_coefficients

FUNCTIONS = (10, 16, 20, 22)
METHODS = ("abc", "abc_shuffle", "abc_reverse")
CONTROLS = ("abc_shuffle", "abc_reverse")
REPEATS = 12
BASE_SEED = 20261231
BUDGET = 10_000
BOOTSTRAP = 10_000
AUDIT_DRAWS = 50_000
AUDIT_SEED = 20261232
COLORS = {"abc_shuffle": "#2a7f91", "abc_reverse": "#b86d3a"}


def read(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError(f"missing original optimizer evidence {path}")
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"empty original optimizer evidence {path}")
    return rows


def write(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("cannot publish an empty dataset")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def exact_sign_p(wins: int, losses: int) -> float:
    count = wins + losses
    return min(
        1.0,
        2 * sum(math.comb(count, j) for j in range(min(wins, losses)+1)) / 2**count,
    )


def verify(source: Path) -> tuple[list[dict], list[dict], list[dict]]:
    trials: list[dict] = []
    history: list[dict] = []
    sources: list[dict] = []
    for fid in FUNCTIONS:
        folder = source / f"f{fid}"
        env = json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
        expected = {
            "function_id": fid, "methods": list(METHODS), "dimension": 30,
            "repeats": REPEATS, "evaluations": BUDGET, "base_seed": BASE_SEED,
            "history_interval": 450, "reference_commit": REFERENCE_COMMIT,
        }
        if any(env.get(k) != value for k, value in expected.items()):
            raise ValueError(f"incorrect frozen metadata for F{fid}")
        if not env.get("source_commit"):
            raise ValueError(f"unverified source commit for F{fid}")
        shard = read(folder/"trials.csv")
        if len(shard) != REPEATS*len(METHODS):
            raise ValueError(f"F{fid} contains an incomplete 36-trial shard")
        trials.extend(shard)
        history.extend(read(folder/"history.csv"))
        sources.append(env)
    allowed = {(fid, seed, method) for fid in FUNCTIONS for seed in range(REPEATS)
               for method in METHODS}
    index = {}
    for row in trials:
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key not in allowed or key in index:
            raise ValueError(f"unexpected/duplicate experiment trial: {key}")
        fid, rep, _ = key
        if (int(row["evaluations"]) != BUDGET or int(row["dimension"]) != 30
                or int(row["seed"]) != BASE_SEED + 10_000*fid + rep):
            raise ValueError(f"invalid budget/seed/dimension {key}")
        if any(not math.isfinite(float(row[k])) for k in
               ("objective", "optimum", "error", "elapsed_seconds")):
            raise ValueError(f"nonfinite numerical trial data {key}")
        if (float(row["error"]) < 0 or
                not math.isclose(
                    float(row["objective"]) - float(row["optimum"]),
                    float(row["error"]), abs_tol=1e-6, rel_tol=1e-10
                )):
            raise ValueError(f"negative or inconsistent objective gap {key}")
        index[key] = row
    if set(index) != allowed or len(trials) != 144:
        raise ValueError("missing unique matched 144 optimization trials")
    trajectories = defaultdict(list)
    for state in history:
        key = (int(state["function_id"]), int(state["repeat"]), state["method"])
        if key not in allowed:
            raise ValueError(f"unexpected original convergence history {key}")
        if (int(state["seed"]) != int(index[key]["seed"])
                or int(state["dimension"]) != 30
                or not math.isfinite(float(state["best_error"]))):
            raise ValueError(f"invalid numerical history record {key}")
        trajectories[key].append(state)
    if set(trajectories) != allowed:
        raise ValueError("original convergence states are missing")
    reference_grid = None
    for key, records in trajectories.items():
        records.sort(key=lambda x: int(x["evaluations"]))
        fes = [int(record["evaluations"]) for record in records]
        errors = [float(record["best_error"]) for record in records]
        if (fes[0] != 100 or fes[-1] != BUDGET or len(set(fes)) != len(fes)
                or any(error < 0 for error in errors)
                or any(curr > prev+1e-7 for prev, curr in pairwise(errors))
                or not math.isclose(errors[-1], float(index[key]["error"]), abs_tol=1e-6)):
            raise ValueError(f"nonmonotone or inconsistent best-so-far evidence {key}")
        if reference_grid is None:
            reference_grid = fes
        if reference_grid != fes:
            raise ValueError(f"inconsistent FE checkpoints {key}")
    for fid in FUNCTIONS:
        for seed in range(REPEATS):
            initial = [
                float(trajectories[(fid, seed, m)][0]["best_error"]) for m in METHODS
            ]
            if max(initial)-min(initial) > 1e-8:
                raise ValueError(f"method initial populations differ F{fid} seed={seed}")
    trials.sort(key=lambda r: (int(r["function_id"]), int(r["repeat"]), r["method"]))
    history.sort(key=lambda r: (
        int(r["function_id"]), int(r["repeat"]), r["method"], int(r["evaluations"])
    ))
    if len(history) != 144*23:
        raise ValueError(f"unexpected sampled FE checkpoint total {len(history)}")
    return trials, history, sources


def bootstrap_statistics(trials: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    index = {(int(r["function_id"]), int(r["repeat"]), r["method"]): r for r in trials}
    if len(index) != 144:
        raise ValueError("statistics require complete 144-trial matched cohort")
    summary, paired, effects = [], [], []
    for fid in FUNCTIONS:
        rng = np.random.default_rng(20261233+fid)
        draws = rng.integers(0, REPEATS, size=(BOOTSTRAP, REPEATS))
        values = {}
        for method in METHODS:
            vals = np.asarray([float(index[(fid, i, method)]["error"])
                               for i in range(REPEATS)])
            values[method] = vals
            ci = np.quantile(vals[draws].mean(axis=1), [0.025, 0.975])
            summary.append({
                "function_id": fid, "method": method, "seeds": REPEATS,
                "mean_error": float(vals.mean()), "median_error": float(np.median(vals)),
                "std_error": float(vals.std(ddof=1)), "bootstrap_mean_ci95_low": float(ci[0]),
                "bootstrap_mean_ci95_high": float(ci[1]),
            })
        for method in CONTROLS:
            delta = np.log1p(values["abc"]) - np.log1p(values[method])
            ci = np.quantile(delta[draws].mean(axis=1), [0.025, 0.975])
            wins = int(np.count_nonzero(delta > 1e-10))
            losses = int(np.count_nonzero(delta < -1e-10))
            paired.append({
                "function_id": fid, "contrast": f"{method}_vs_abc",
                "control_wins": wins, "abc_wins": losses,
                "ties": REPEATS-wins-losses,
                "paired_mean_log1p_gain": float(delta.mean()),
                "bootstrap_ci95_low": float(ci[0]),
                "bootstrap_ci95_high": float(ci[1]),
                "exact_sign_p": exact_sign_p(wins, losses), "holm_sign_p": 1.0,
            })
            for rep, value in enumerate(delta):
                effects.append({
                    "function_id": fid, "repeat": rep, "method": method,
                    "paired_log1p_gain": float(value),
                })
    holm = 0.0
    for rank, i in enumerate(sorted(range(8), key=lambda i: paired[i]["exact_sign_p"])):
        holm = max(holm, min(1.0, paired[i]["exact_sign_p"]*(8-rank)))
        paired[i]["holm_sign_p"] = holm
    return summary, paired, effects


def coefficient_audit() -> tuple[list[dict], dict]:
    rng = np.random.default_rng(AUDIT_SEED)
    matrix = np.empty((AUDIT_DRAWS, 15), dtype=np.float64)
    for n in range(AUDIT_DRAWS):
        result = adaptive_boundary_coefficients(15, rng)
        if result.attempts != 1 or not is_valid_coefficients(result.coefficients):
            raise ValueError("invalid coefficient sampler evidence")
        matrix[n] = result.coefficients
    rows = []
    for idx in range(15):
        a = matrix[:, idx]
        q25, med, q75 = np.quantile(a, [0.25, 0.5, 0.75])
        rows.append({
            "index": idx+1, "elite_parent_slot": idx < 5,
            "draws": AUDIT_DRAWS, "mean_alpha": float(np.mean(a)),
            "median_alpha": float(med), "q25_alpha": float(q25),
            "q75_alpha": float(q75), "mean_abs_alpha": float(np.mean(np.abs(a))),
            "std_alpha": float(np.std(a, ddof=1)),
        })
    elite_abs = float(np.mean(np.abs(matrix[:, :5]).sum(axis=1)))
    nonelite_abs = float(np.mean(np.abs(matrix[:, 5:]).sum(axis=1)))
    overview = {
        "total_draws": AUDIT_DRAWS, "rng_seed": AUDIT_SEED,
        "parents": 15, "elite_parents": 5,
        "mean_elite_absolute_mass": elite_abs,
        "mean_nonelite_absolute_mass": nonelite_abs,
        "mean_elite_share_absolute_mass": float(
            np.mean(np.abs(matrix[:, :5]).sum(axis=1) /
                    np.abs(matrix).sum(axis=1))
        ),
    }
    return rows, overview


def svg_start(w: int, h: int, title: str, note: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">',
        f'<rect width="{w}" height="{h}" fill="#f8fafc"/>',
        f'<text x="55" y="59" font-family="Arial" font-weight="700" font-size="27" fill="#172d46">{escape(title)}</text>',
        f'<text x="55" y="88" font-family="Arial" font-size="15" fill="#54657a">{escape(note)}</text>',
    ]


def effects_svg(paired: list[dict], effects: list[dict]) -> str:
    out = svg_start(
        1200, 860, "Coefficient position | Paired seed effects",
        "144 real 10k-FE optimization trials · 12 fresh matched seeds · positive favors the positional control",
    )
    rows = {(int(t["function_id"]), t["contrast"]): t for t in paired}
    data = defaultdict(list)
    for row in effects:
        data[(int(row["function_id"]), row["method"])].append(float(row["paired_log1p_gain"]))
    axis = max(
        0.12, max(abs(float(t[k])) for t in paired
                  for k in ("bootstrap_ci95_low", "bootstrap_ci95_high"))*1.30,
        max(abs(v) for vals in data.values() for v in vals)*1.07,
    )
    left, width = 343.0, 632.0
    to_x = lambda val: left + width*(val+axis)/(2*axis)
    for idx, fid in enumerate(FUNCTIONS):
        y_top = 150 + idx*157
        out.append(f'<rect x="50" y="{y_top-32}" width="1090" height="147" rx="15" fill="#ffffff" stroke="#e0e7ee"/>')
        out.append(f'<text x="74" y="{y_top+15}" font-family="Arial" font-size="21" font-weight="700" fill="#17304b">F{fid}</text>')
        out.append(f'<line x1="{to_x(0):.2f}" y1="{y_top-10}" x2="{to_x(0):.2f}" y2="{y_top+99}" stroke="#94a3b8" stroke-dasharray="5 4"/>')
        for j, method in enumerate(CONTROLS):
            y = y_top + 11 + 66*j
            v = rows[(fid, f"{method}_vs_abc")]
            lo, hi = float(v["bootstrap_ci95_low"]), float(v["bootstrap_ci95_high"])
            mean = float(v["paired_mean_log1p_gain"])
            color = COLORS[method]
            out.append(f'<text x="133" y="{y+5}" font-size="16" fill="{color}" font-family="Arial" font-weight="700">{escape(method.upper())}</text>')
            for k, val in enumerate(data[(fid, method)]):
                x = to_x(val)
                jitter = (k%5-2)*4
                out.append(f'<circle cx="{x:.2f}" cy="{y+jitter:.1f}" r="4.7" fill="{color}" fill-opacity="0.7" stroke="white" stroke-width="0.7"/>')
            out.append(f'<line x1="{to_x(lo):.2f}" y1="{y+19}" x2="{to_x(hi):.2f}" y2="{y+19}" stroke="#0f172a" stroke-width="4"/>')
            out.append(f'<circle cx="{to_x(mean):.2f}" cy="{y+19}" r="5.5" fill="#0f172a"/>')
            out.append(f'<text x="995" y="{y+5}" font-family="Arial" font-size="13" fill="#475569">Holm p={float(v["holm_sign_p"]):.3g}</text>')
    for val in (-axis, 0.0, axis):
        out.append(f'<text x="{to_x(val):.1f}" y="803" font-family="Arial" font-size="14" text-anchor="middle" fill="#475569">{val:+.2f}</text>')
    out.append('<text x="56" y="838" font-family="Arial" font-size="13" fill="#64748b">Dots = paired seed log1p gains; black whisker = 95% paired bootstrap interval; Holm corrects eight tests.</text>')
    out.append("</svg>")
    text = "\n".join(out)+"\n"
    ElementTree.fromstring(text)
    return text


def coefficient_svg(rows: list[dict], overview: dict) -> str:
    out = svg_start(
        1220, 690, "ABC coefficient position | Marginal distribution",
        "50,000 valid vectors · M=15 parents · first 5 slots assigned to elites · descriptive Monte Carlo",
    )
    x0, top, height, width = 120.0, 156.0, 374.0, 1010.0
    low, high = -0.55, 1.55
    yy = lambda val: top+height*(high-val)/(high-low)
    for ref in (-0.5, 0.0, 0.5, 1.0, 1.5):
        y = yy(ref)
        out.append(f'<line x1="{x0:.0f}" y1="{y:.2f}" x2="{x0+width:.0f}" y2="{y:.2f}" stroke="#e5edf4"/>')
        out.append(f'<text x="{x0-12:.0f}" y="{y+4:.2f}" font-family="Arial" font-size="13" text-anchor="end" fill="#64748b">{ref:+.1f}</text>')
    slot = width/15.0
    for row in rows:
        i = int(row["index"])
        x = x0+(i-0.5)*slot
        color = "#216c8c" if i <= 5 else "#b87537"
        lower, median, upper = (float(row[k]) for k in
                                ("q25_alpha", "median_alpha", "q75_alpha"))
        mean = float(row["mean_alpha"])
        out.append(f'<line x1="{x:.2f}" y1="{yy(lower):.2f}" x2="{x:.2f}" y2="{yy(upper):.2f}" stroke="{color}" stroke-width="12" stroke-linecap="round" stroke-opacity="0.27"/>')
        out.append(f'<line x1="{x-11:.2f}" y1="{yy(median):.2f}" x2="{x+11:.2f}" y2="{yy(median):.2f}" stroke="{color}" stroke-width="4"/>')
        out.append(f'<circle cx="{x:.2f}" cy="{yy(mean):.2f}" r="5" fill="{color}" stroke="white" stroke-width="1.2"/>')
        out.append(f'<text x="{x:.2f}" y="554" font-family="Arial" font-size="14" text-anchor="middle" fill="#475569">{i}</text>')
    out.append(f'<line x1="{x0+5*slot:.2f}" y1="142" x2="{x0+5*slot:.2f}" y2="565" stroke="#a3b5c8" stroke-width="1.6" stroke-dasharray="5 4"/>')
    out.append('<text x="235" y="610" font-family="Arial" font-weight="700" fill="#216c8c" font-size="15">Elite-parent positions (1–5)</text>')
    out.append('<text x="695" y="610" font-family="Arial" font-weight="700" fill="#b87537" font-size="15">Non-elite positions (6–15)</text>')
    out.append(f'<text x="69" y="650" font-family="Arial" font-size="14" fill="#334155">Elite share of total absolute coefficient mass: {overview["mean_elite_share_absolute_mass"]:.3f} (descriptive; not causal)</text>')
    out.append('<text x="69" y="675" font-family="Arial" font-size="13" fill="#64748b">Thick strokes: 25–75% range · horizontal ticks: medians · dots: means · all vectors pass affine feasibility.</text>')
    out.append("</svg>")
    text = "\n".join(out)+"\n"
    ElementTree.fromstring(text)
    return text


def report(summary: list[dict], comparisons: list[dict], overview: dict) -> str:
    lookup = {(int(r["function_id"]), r["method"]): r for r in summary}
    out = [
        "# ABC coefficient position: 144-trial three-arm mechanism study",
        "",
        "This prerecording-followed exploratory experiment runs the unmodified "
        "ABC generator, stochastic ABC-Shuffle and deterministic **ABC-Reverse**. "
        "Reversal consumes **zero additional random draws** while preserving "
        "the exact original ABC coefficient multiset, affine sum and validity. "
        "The new 12-seed cohort is independent of previous cohorts, but the "
        "four functions were selected adaptively after earlier results.",
        "",
        "## Mean final objective error (lower is better)",
        "",
        "| Function | ABC | ABC-Shuffle | ABC-Reverse |",
        "|:---|---:|---:|---:|",
    ]
    for fid in FUNCTIONS:
        out.append(
            f"| F{fid} | {float(lookup[(fid, 'abc')]['mean_error']):,.3f} | "
            f"{float(lookup[(fid, 'abc_shuffle')]['mean_error']):,.3f} | "
            f"{float(lookup[(fid, 'abc_reverse')]['mean_error']):,.3f} |"
        )
    out.extend([
        "",
        "## Eight paired exact sign tests (all Holm-adjusted together)",
        "",
        "| Function | Positional control | Control W/L/T | Mean paired log1p gain | 95% paired bootstrap CI | Holm p |",
        "|:---|:---|---:|---:|:---|---:|",
    ])
    for r in comparisons:
        out.append(
            f"| F{r['function_id']} | {r['contrast']} | "
            f"{r['control_wins']}/{r['abc_wins']}/{r['ties']} | "
            f"{float(r['paired_mean_log1p_gain']):+.4f} | "
            f"[{float(r['bootstrap_ci95_low']):+.4f}, "
            f"{float(r['bootstrap_ci95_high']):+.4f}] | "
            f"{float(r['holm_sign_p']):.5g} |"
        )
    out.extend([
        "",
        "Positive paired log1p gain means the positional control has lower error "
        "than ABC. Exact sign tests quantify the direction of the paired "
        "outcome, not directly the mean-error comparison. Multiple testing "
        "outside this eight-comparison family is not controlled.",
        "",
        "## Generator-level positional distribution audit (not optimizer runs)",
        "",
        f"Generated {AUDIT_DRAWS:,} independent valid ABC coefficient vectors "
        "at M=15, using audit seed 20261232. "
        f"The first five elite-assigned positions carry on average "
        f"{overview['mean_elite_share_absolute_mass']*100:.2f}% of total "
        "absolute coefficient mass. A position-specific sampling distribution "
        "is consistent with the potential rank-coupling mechanism, but "
        "neither the coefficient statistic nor the optimizer ablation alone "
        "proves a causal benefit.",
        "",
        "## Scientific limitations",
        "",
        "- The functions are an adaptively selected CEC2017 subset, not all 29 functions.",
        "- ABC-Reverse is a deterministic extreme order assignment, not a random "
        "permutation test. It avoids ABC-Shuffle's extra RNG draws but does not "
        "hold later populations or coefficient draws identical after trajectories diverge.",
        "- Each method has the same population, fresh paired initial seeds, and "
        "10k function-evaluation budget. Wall-clock compute cost is separately observed.",
        "- The fixed C-derived Python reference backend is not the organizer's "
        "official C executable. Do not claim general algorithm dominance.",
        "",
        "## Original data and figures",
        "",
        "[144 original optimizer trials](trials.csv) · "
        "[3,312 convergence records](history.csv) · "
        "[12 method summaries](summary.csv) · "
        "[eight Holm contrasts](paired_tests.csv) · "
        "[all per-seed paired effects](paired_effects.csv) · "
        "[50,000-draw generator marginal diagnostics](coefficient_position_audit.csv) · "
        "[coefficient audit overview](coefficient_audit.json) · "
        "[frozen protocol](../../abc_reverse_mechanism_protocol.md)",
        "",
    ])
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--figure-dir", required=True, type=Path)
    args = parser.parse_args()
    trials, history, manifests = verify(args.input_dir)
    summary, comparisons, effects = bootstrap_statistics(trials)
    audit, overview = coefficient_audit()
    out = args.output_dir
    for name, rows in (
        ("trials.csv", trials), ("history.csv", history),
        ("summary.csv", summary), ("paired_tests.csv", comparisons),
        ("paired_effects.csv", effects), ("coefficient_position_audit.csv", audit),
    ):
        write(out/name, rows)
    (out/"coefficient_audit.json").write_text(
        json.dumps(overview, indent=2)+"\n", encoding="utf-8"
    )
    manifest = {
        "functions": list(FUNCTIONS), "methods": list(METHODS),
        "evaluations": BUDGET, "dimension": 30, "repeats": REPEATS,
        "base_seed": BASE_SEED, "trials": len(trials), "history_rows": len(history),
        "reference_commit": REFERENCE_COMMIT, "audit_draws": AUDIT_DRAWS,
        "audit_seed": AUDIT_SEED, "paired_bootstrap_resamples": BOOTSTRAP,
        "source_manifests": manifests,
        "study_type": "exploratory, prospective three-arm coefficient-order mechanism",
        "python": sys.version, "numpy": np.__version__,
        "platform": platform.platform(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (out/"environment.json").write_text(
        json.dumps(manifest, indent=2)+"\n", encoding="utf-8"
    )
    (out/"report.md").write_text(report(summary, comparisons, overview), encoding="utf-8")
    figures = {
        "cec2017-coefficient-rank-144-paired-effects.svg": effects_svg(comparisons, effects),
        "cec2017-abc-50000-coefficient-position.svg": coefficient_svg(audit, overview),
    }
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    for filename, svg in figures.items():
        (args.figure_dir/filename).write_text(svg, encoding="utf-8")
    print(f"Validated {len(trials)} actual new runs and {len(history)} checkpoint rows; "
          f"generated 2 original-data figures and 50,000 coefficient samples.")


if __name__ == "__main__":
    main()
