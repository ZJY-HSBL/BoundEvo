"""Data-derived anytime-performance research and publication-quality SVG figures.

All analyses use 120 verified actual F16/F22 100k-FE optimizer trajectories.
No surrogate/synthetic records are published. No optional plotting dependency.
"""

from __future__ import annotations

from itertools import pairwise

import argparse
import csv
import math
import random
import statistics
from collections import defaultdict
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/experiments/cec2017-paperbudget-30d-100k-20seeds-2026-10-19"
TARGET = ROOT / "docs/experiments/cec2017-anytime-30d-100k-20seeds-2026-10-20"
FIGURES = ROOT / "docs/figures"
METHODS = ("abc", "edbf", "re")
FUNCTIONS = (16, 22)
COLORS = {"abc": "#12618a", "edbf": "#be6d2a", "re": "#258473"}
SAMPLES = 10_000
SEED = 20261020
FIRST = "<!-- ADVANCED_RESEARCH_START -->"
LAST = "<!-- ADVANCED_RESEARCH_END -->"


def read(name: str) -> list[dict]:
    path = SOURCE / name
    if not path.is_file():
        raise ValueError(f"missing published original scientific data: {path}")
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def quantile(values: list[float], q: float) -> float:
    seq = sorted(values)
    if not seq or not 0 <= q <= 1:
        raise ValueError("invalid quantile")
    z = (len(seq) - 1) * q
    lower = int(z)
    upper = min(lower + 1, len(seq) - 1)
    return seq[lower] + (seq[upper] - seq[lower]) * (z - lower)


def sign_p(wins: int, losses: int) -> float:
    n = wins + losses
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(wins, losses) + 1)) / 2**n)


def anytime_loss(points: list[tuple[int, float]]) -> float:
    """Sample-and-hold integral of log1p(error) over log(FE) in [10k,100k]."""
    sub = [(int(fe), float(err)) for fe, err in points if fe >= 10_000]
    if len(sub) < 2 or sub[0][0] != 10_000 or sub[-1][0] != 100_000:
        raise ValueError("need exact 10k and 100k historical evaluation records")
    width = math.log(10)
    total = 0.0
    for (left, previous), (right, current) in pairwise(sub):
        if not (left < right and 0 <= current <= previous + 1e-7):
            raise ValueError("nonmonotone or duplicate sample-and-hold trace")
        total += math.log1p(previous) * math.log(right / left)
    return total / width


def verify() -> tuple[dict, dict, list[int]]:
    trials = read("trials.csv")
    history = read("history.csv")
    expected = {(f, r, m) for f in FUNCTIONS for r in range(20) for m in METHODS}
    indexed = {}
    traces = defaultdict(list)
    for t in trials:
        k = (int(t["function_id"]), int(t["repeat"]), t["method"])
        if k in indexed or k not in expected:
            raise ValueError("unexpected or duplicate original 100k trial")
        if int(t["evaluations"]) != 100_000:
            raise ValueError("unexpected original FE budget")
        indexed[k] = t
    if set(indexed) != expected or len(trials) != 120 or len(history) != 13_440:
        raise ValueError("original 120-trial evidence is incomplete")
    for h in history:
        k = (int(h["function_id"]), int(h["repeat"]), h["method"])
        if k not in expected:
            raise ValueError("unknown convergence trajectory")
        traces[k].append((int(h["evaluations"]), float(h["best_error"])))
    if set(traces) != expected:
        raise ValueError("missing original convergence evidence")
    steps = None
    for k, record in indexed.items():
        series = sorted(traces[k])
        if (series[0][0] != 100 or series[-1][0] != 100_000
                or len(series) != 112 or len({p[0] for p in series}) != len(series)
                or any(e < 0 or not math.isfinite(e) for _, e in series)
                or any(b[1] > a[1] + 1e-7 for a, b in pairwise(series))):
            raise ValueError(f"invalid real best-so-far series {k}")
        reference = float(record["baseline_10k_error"])
        midpoint = [v for x, v in series if x == 10_000]
        if len(midpoint) != 1 or not math.isclose(
            midpoint[0], reference, rel_tol=1e-9, abs_tol=1e-6
        ):
            raise ValueError(f"original historical 10k prefix mismatch {k}")
        if not math.isclose(series[-1][1], float(record["error"]), abs_tol=1e-6):
            raise ValueError(f"100k endpoint mismatches original CSV {k}")
        if steps is None:
            steps = [x for x, _ in series]
        if steps != [x for x, _ in series]:
            raise ValueError("cannot aggregate incompatible sample checkpoint grids")
        traces[k] = series
    assert steps is not None
    return indexed, traces, steps


def analyse(indexed: dict, traces: dict, steps: list[int]) -> tuple[list[dict], list[dict], list[dict]]:
    area = {k: anytime_loss(points) for k, points in traces.items()}
    summary, tests, profiles = [], [], []
    for fid in FUNCTIONS:
        rng = random.Random(SEED + fid)
        draws = [[rng.randrange(20) for _ in range(20)] for _ in range(SAMPLES)]
        threshold_data = [
            float(indexed[(fid, seed, m)]["baseline_10k_error"])
            for seed in range(20) for m in METHODS
        ]
        targets = [quantile(threshold_data, q) for q in (0.25, 0.5, 0.75)]
        values = {}
        for m in METHODS:
            a = [area[(fid, seed, m)] for seed in range(20)]
            values[m] = a
            boot = [statistics.fmean(a[i] for i in draw) for draw in draws]
            summary.append({
                "function_id": fid, "method": m, "seeds": 20,
                "mean_log_budget_loss": statistics.fmean(a),
                "median_log_budget_loss": statistics.median(a),
                "bootstrap_mean_ci95_low": quantile(boot, 0.025),
                "bootstrap_mean_ci95_high": quantile(boot, 0.975),
            })
            ordered = [dict(traces[(fid, seed, m)]) for seed in range(20)]
            for fe in (10_000, 20_000, 30_000, 40_000, 50_000,
                       60_000, 70_000, 80_000, 90_000, 100_000):
                # Conservative first sampled checkpoint: last observation <= FE.
                hits = 0
                for trace in ordered:
                    latest = max(x for x in trace if x <= fe)
                    for target in targets:
                        if trace[latest] <= target:
                            hits += 1
                profiles.append({
                    "function_id": fid, "method": m, "evaluations": fe,
                    "pooled_10k_q25_target": targets[0],
                    "pooled_10k_q50_target": targets[1],
                    "pooled_10k_q75_target": targets[2],
                    "targets_reached": hits, "total_target_pairs": 60,
                    "attainment_fraction": hits / 60,
                })
        for other in ("edbf", "re"):
            difference = [values[other][i] - values["abc"][i] for i in range(20)]
            boot = [statistics.fmean(difference[i] for i in draw) for draw in draws]
            wins = sum(x > 1e-10 for x in difference)
            losses = sum(x < -1e-10 for x in difference)
            tests.append({
                "function_id": fid, "contrast": f"abc_vs_{other}",
                "abc_wins": wins, "abc_losses": losses,
                "ties": 20 - wins - losses,
                "mean_paired_log_budget_advantage": statistics.fmean(difference),
                "bootstrap_paired_ci95_low": quantile(boot, 0.025),
                "bootstrap_paired_ci95_high": quantile(boot, 0.975),
                "exact_sign_p": sign_p(wins, losses), "holm_sign_p": 1.0,
            })
    adjusted = 0.0
    for rank, i in enumerate(sorted(range(len(tests)), key=lambda i: tests[i]["exact_sign_p"])):
        adjusted = max(adjusted, min(1.0, tests[i]["exact_sign_p"] * (4 - rank)))
        tests[i]["holm_sign_p"] = adjusted
    return summary, tests, profiles


def svg_start(width: int, height: int, title: str, subtitle: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
        f'<rect width="{width}" height="{height}" fill="#f8fafc"/>',
        f'<text x="54" y="56" font-size="27" font-weight="700" fill="#14263e" '
        f'font-family="Arial,sans-serif">{escape(title)}</text>',
        f'<text x="54" y="86" font-size="15" fill="#53657a" '
        f'font-family="Arial,sans-serif">{escape(subtitle)}</text>',
    ]


def txt(x: float, y: float, text: str, size: int = 14, color: str = "#334155",
        anchor: str = "start", weight: str = "400") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}" '
            f'font-family="Arial,sans-serif">{escape(str(text))}</text>')


def path(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{'M' if i == 0 else 'L'}{x:.2f},{y:.2f}" for i, (x, y) in enumerate(points))


def poly(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def svg_ribbons(traces: dict, steps: list[int]) -> str:
    content = svg_start(1190, 640, "Anytime convergence | Median and seed variability",
                        "CEC2017 30D · n=20 paired seeds per method · actual best-so-far checkpoints · lower is better")
    grid = [x for x in steps if x >= 10_000]
    for idx, fid in enumerate(FUNCTIONS):
        x0, y0, w, h = 74 + 590 * idx, 164, 485, 362
        content.append(f'<rect x="{x0-12}" y="{y0-48}" width="{w+44}" height="{h+100}" '
                       'rx="12" fill="#ffffff" stroke="#e2e8f0"/>')
        content.append(txt(x0, y0-20, f"F{fid} · 10k to 100k FE", 21, "#172c45", weight="700"))
        all_values = [v for r in range(20) for m in METHODS
                      for fe, v in traces[(fid, r, m)] if fe >= 10_000]
        ymin, ymax = min(all_values), max(all_values)
        pad = max(1.0, (ymax-ymin)*0.12)
        ymin = max(0.0, ymin - pad)
        ymax += pad
        fx = lambda fe: x0 + w * (math.log(fe/10_000) / math.log(10))
        fy = lambda v: y0 + h * (ymax-v)/(ymax-ymin)
        for k in range(5):
            value = ymin + (ymax-ymin)*k/4
            y = fy(value)
            content.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+w}" y2="{y:.1f}" '
                           'stroke="#e8eef4" stroke-width="1"/>')
            content.append(txt(x0-10, y+5, f"{value:,.0f}", 12, "#64748b", anchor="end"))
        for fe in (10_000, 20_000, 50_000, 100_000):
            x = fx(fe)
            content.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y0+h}" '
                           'stroke="#eef2f7" stroke-width="1"/>')
            content.append(txt(x, y0+h+27, f"{fe//1000}k", 13, anchor="middle"))
        for m in METHODS:
            lookup = [dict(traces[(fid, seed, m)]) for seed in range(20)]
            q25 = [quantile([d[fe] for d in lookup], 0.25) for fe in grid]
            q50 = [quantile([d[fe] for d in lookup], 0.5) for fe in grid]
            q75 = [quantile([d[fe] for d in lookup], 0.75) for fe in grid]
            upper = [(fx(fe), fy(v)) for fe, v in zip(grid, q75)]
            lower = [(fx(fe), fy(v)) for fe, v in zip(grid, q25)]
            median = [(fx(fe), fy(v)) for fe, v in zip(grid, q50)]
            color = COLORS[m]
            content.append(f'<polygon points="{poly(upper + list(reversed(lower)))}" '
                           f'fill="{color}" fill-opacity="0.12"/>')
            content.append(f'<path d="{path(median)}" fill="none" stroke="{color}" '
                           'stroke-width="3" stroke-linejoin="round"/>')
    for i, m in enumerate(METHODS):
        x = 345 + 190 * i
        content.append(f'<line x1="{x}" y1="591" x2="{x+38}" y2="591" '
                       f'stroke="{COLORS[m]}" stroke-width="4"/>')
        content.append(txt(x+46, 596, f"{m.upper()} · median", 14))
    content.append(txt(72, 624, "Shaded bands: per-seed interquartile range (IQR); not confidence intervals.", 12))
    return "\n".join(content + ["</svg>"]) + "\n"


def svg_paired(indexed: dict) -> str:
    content = svg_start(1150, 925, "Paired-seed endpoint comparison",
                        "20 matched seeds · each dot is one actual paired trial · above diagonal = ABC lower error")
    for col, fid in enumerate(FUNCTIONS):
        for row, other in enumerate(("edbf", "re")):
            x0, y0, w, h = 105 + 530*col, 177 + 365*row, 340, 260
            points = [(float(indexed[(fid, s, "abc")]["error"]),
                       float(indexed[(fid, s, other)]["error"])) for s in range(20)]
            maxval = max(max(x, y) for x, y in points) * 1.08
            maxval = max(maxval, 1e-12)
            content.append(f'<rect x="{x0-68}" y="{y0-58}" width="{w+121}" '
                           f'height="{h+104}" rx="14" fill="white" stroke="#e2e8f0"/>')
            content.append(txt(x0, y0-30, f"F{fid}  ·  ABC vs {other.upper()}", 20, weight="700"))
            content.append(f'<line x1="{x0}" y1="{y0+h}" x2="{x0+w}" y2="{y0}" '
                           'stroke="#94a3b8" stroke-dasharray="7 5" stroke-width="2"/>')
            for tick in (0, 0.5, 1):
                xx, yy = x0 + w*tick, y0 + h*(1-tick)
                content.append(f'<line x1="{xx:.1f}" y1="{y0+h}" x2="{xx:.1f}" y2="{y0+h+6}" stroke="#64748b"/>')
                content.append(f'<line x1="{x0-6}" y1="{yy:.1f}" x2="{x0}" y2="{yy:.1f}" stroke="#64748b"/>')
                content.append(txt(xx, y0+h+25, f"{maxval*tick:,.0f}", 11, anchor="middle"))
                content.append(txt(x0-9, yy+4, f"{maxval*tick:,.0f}", 11, anchor="end"))
            for a, b in points:
                xx, yy = x0 + w*a/maxval, y0 + h*(1-b/maxval)
                content.append(f'<circle cx="{xx:.2f}" cy="{yy:.2f}" r="5.5" '
                               f'fill="{COLORS[other]}" fill-opacity="0.76" stroke="white" stroke-width="1"/>')
            wins = sum(a < b - 1e-9 for a, b in points)
            content.append(txt(x0+w/2, y0+h+51, f"ABC endpoint error · ABC wins {wins}/20", 12, anchor="middle"))
    content.append(txt(65, 907, "Dots above diagonal favor ABC; paired seed identity is preserved, not independently resampled.", 13))
    return "\n".join(content+["</svg>"]) + "\n"


def svg_ecdf(profiles: list[dict]) -> str:
    content = svg_start(1170, 625, "Target-attainment profiles | 10k–100k evaluations",
                        "Targets = pooled 10k error quartiles · 3 targets × 20 seeds per method · sampled first-hits")
    idx = {(int(r["function_id"]), r["method"], int(r["evaluations"])): r for r in profiles}
    for column, fid in enumerate(FUNCTIONS):
        x0, y0, w, h = 78 + 570*column, 166, 465, 350
        content.append(f'<rect x="{x0-21}" y="{y0-49}" width="{w+45}" height="{h+102}" '
                       'rx="14" fill="white" stroke="#e2e8f0"/>')
        content.append(txt(x0, y0-23, f"F{fid} · pooled 10k thresholds", 20, weight="700"))
        for pct in (0, 25, 50, 75, 100):
            y = y0 + h*(1-pct/100)
            content.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+w}" y2="{y:.1f}" '
                           'stroke="#e8eef5"/>')
            content.append(txt(x0-9, y+4, f"{pct}%", 12, anchor="end"))
        for fe in (10_000, 50_000, 100_000):
            x = x0 + w*(fe-10_000)/90_000
            content.append(txt(x, y0+h+26, f"{fe//1000}k", 12, anchor="middle"))
        for m in METHODS:
            pts = [(x0 + w*(fe-10_000)/90_000,
                    y0 + h*(1-float(idx[(fid, m, fe)]["attainment_fraction"])))
                   for fe in range(10_000, 100_001, 10_000)]
            content.append(f'<path d="{path(pts)}" stroke="{COLORS[m]}" fill="none" '
                           'stroke-width="3.2" stroke-linejoin="round"/>')
            for x, y in pts:
                content.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.0" fill="{COLORS[m]}"/>')
        sample = idx[(fid, "abc", 10_000)]
        content.append(txt(x0, y0+h+49, f"Baseline targets: {float(sample['pooled_10k_q25_target']):,.0f} / "
                           f"{float(sample['pooled_10k_q50_target']):,.0f} / "
                           f"{float(sample['pooled_10k_q75_target']):,.0f}", 12))
    for i, m in enumerate(METHODS):
        xx = 353+178*i
        content.append(f'<line x1="{xx}" y1="596" x2="{xx+31}" y2="596" '
                       f'stroke="{COLORS[m]}" stroke-width="4"/>')
        content.append(txt(xx+38, 601, m.upper(), 14))
    return "\n".join(content+["</svg>"]) + "\n"


def svg_auc(tests: list[dict]) -> str:
    content = svg_start(1120, 560, "Anytime loss | Paired advantage over ABC",
                        "Difference = comparator minus ABC in log-budget-averaged log1p(error) · positive favors ABC")
    vals = [float(t[key]) for t in tests for key in
            ("bootstrap_paired_ci95_low", "bootstrap_paired_ci95_high")]
    bound = max(0.12, max(abs(v) for v in vals)*1.20)
    x0, x1 = 390, 940
    def xp(v: float) -> float:
        return x0 + (v+bound)/(2*bound)*(x1-x0)
    content.append(f'<line x1="{xp(0):.1f}" y1="145" x2="{xp(0):.1f}" y2="457" '
                   'stroke="#475569" stroke-width="2" stroke-dasharray="5 4"/>')
    for i, t in enumerate(tests):
        y = 182+80*i
        lo = float(t["bootstrap_paired_ci95_low"])
        hi = float(t["bootstrap_paired_ci95_high"])
        mean = float(t["mean_paired_log_budget_advantage"])
        f = int(t["function_id"])
        method = t["contrast"].split("_")[-1]
        content.append(txt(58, y+6, f"F{f} · ABC vs {method.upper()}", 17, weight="700"))
        content.append(f'<line x1="{xp(lo):.2f}" y1="{y}" x2="{xp(hi):.2f}" '
                       f'y2="{y}" stroke="{COLORS[method]}" stroke-width="4"/>')
        for endpoint in (lo, hi):
            content.append(f'<line x1="{xp(endpoint):.2f}" y1="{y-10}" '
                           f'x2="{xp(endpoint):.2f}" y2="{y+10}" '
                           f'stroke="{COLORS[method]}" stroke-width="3"/>')
        content.append(f'<circle cx="{xp(mean):.2f}" cy="{y}" r="7.5" '
                       f'fill="{COLORS[method]}" stroke="#ffffff" stroke-width="2"/>')
        content.append(txt(958, y+6, f"Holm p={float(t['holm_sign_p']):.3g}", 14))
        content.append(txt(958, y+24, f"W/L {t['abc_wins']}/{t['abc_losses']}", 12, "#64748b"))
    for i in range(5):
        value = -bound + bound*i/2
        content.append(txt(xp(value), 479, f"{value:+.2f}", 12, anchor="middle"))
    content.append(txt(530, 523, "95% paired-seed bootstrap intervals · all four sign tests jointly Holm-adjusted",
                       13, anchor="middle"))
    return "\n".join(content+["</svg>"])+"\n"


def write_csv(rows: list[dict]) -> str:
    import io
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def report(summary: list[dict], tests: list[dict], profiles: list[dict]) -> str:
    lines = [
        "# CEC2017 F16/F22 anytime research: measured 10k–100k trajectories", "",
        "Reuse the previously completed **120 real 100k-evaluation optimization runs**, "
        "20 paired seeds per method/function. This is a **new analysis of existing "
        "trajectories, not 120 additional runs**.", "",
        "Following the anytime-performance view of black-box optimization, the "
        "primary exploratory outcome is the sample-and-hold integral of "
        "`log1p(best-so-far error)` over `log(FE)` from FE=10,000 to "
        "FE=100,000, divided by `log(10)`. Smaller means better anytime "
        "performance. The checkpoint step approximation does not reconstruct "
        "changes between measurements.", "",
        "## Log-budget anytime loss (lower is better)", "",
        "| Function | Method | Mean | 95% bootstrap mean CI |",
        "|:---|:---|---:|:---|",
    ]
    for r in summary:
        lines.append(
            f"| F{r['function_id']} | {r['method'].upper()} | "
            f"{r['mean_log_budget_loss']:.5f} | "
            f"[{r['bootstrap_mean_ci95_low']:.5f}, "
            f"{r['bootstrap_mean_ci95_high']:.5f}] |"
        )
    lines += [
        "", "## Paired anytime contrast and uncertainty", "",
        "| Function | Contrast | ABC W/L/T | mean comparator−ABC | Bootstrap 95% CI | Holm p |",
        "|:---|:---|---:|---:|:---|---:|",
    ]
    for t in tests:
        lines.append(
            f"| F{t['function_id']} | {t['contrast']} | "
            f"{t['abc_wins']}/{t['abc_losses']}/{t['ties']} | "
            f"{t['mean_paired_log_budget_advantage']:+.5f} | "
            f"[{t['bootstrap_paired_ci95_low']:+.5f}, "
            f"{t['bootstrap_paired_ci95_high']:+.5f}] | "
            f"{t['holm_sign_p']:.6g} |"
        )
    lines += [
        "", "## Fixed baseline-derived target profiles", "",
        "For each function, take the 25th, 50th, 75th percentiles of 60 pooled "
        "10k-FE endpoint errors across all methods. Each method has 20 seeds "
        "× 3 thresholds = 60 descriptive target-seed pairs. Percentages show "
        "pairs whose best error reached the respective target **at a sampled "
        "checkpoint by the stated FE budget**. Targets were chosen after "
        "seeing the 10k historical values and are not blinded confirmation.", "",
        "| Function | Method | 10k attainment | 100k attainment |",
        "|:---|:---|---:|---:|",
    ]
    lookup = {(int(r["function_id"]), r["method"], int(r["evaluations"])): r
              for r in profiles}
    for fid in FUNCTIONS:
        for m in METHODS:
            a = lookup[(fid, m, 10_000)]
            b = lookup[(fid, m, 100_000)]
            lines.append(
                f"| F{fid} | {m.upper()} | "
                f"{100*float(a['attainment_fraction']):.1f}% | "
                f"{100*float(b['attainment_fraction']):.1f}% |"
            )
    lines += [
        "", "## Integrity and interpretation", "",
        "- All 120 experimental keys and 13,440 history rows verified; all trajectories "
        "have 112 unique checkpoints, exact original 10k and 100k outcomes and "
        "monotone best-so-far records.",
        "- Bootstrap replicates re-sample **paired seed indices** rather than "
        "treating four comparisons, many times, or three targets as independent.",
        "- Exact two-sided paired sign tests were Holm-adjusted for the four "
        "within-analysis comparisons. This exploratory analysis is post-hoc and "
        "does not adjust for other comparisons made across previous releases.",
        "- Within-function objectives can be compared across methods; absolute "
        "errors are not pooled across differently scaled F16 and F22 landscapes.",
        "- Reference-derived CEC2017 Python backend, not the official C binary. "
        "The two functions were selected adaptively in earlier work.", "",
        "## Sources", "",
        "[120 published original trials](../cec2017-paperbudget-30d-100k-20seeds-2026-10-19/trials.csv) · "
        "[13,440 original convergence states](../cec2017-paperbudget-30d-100k-20seeds-2026-10-19/history.csv) · "
        "[new anytime summaries](anytime_summary.csv) · "
        "[four paired contrasts](anytime_paired.csv) · "
        "[empirical attainment profiles](target_profiles.csv) · "
        "[recorded protocol](../../fresh_function_replication_protocol.md)", "",
    ]
    return "\n".join(lines)


def readme_block(language: str, summary: list[dict], tests: list[dict],
                 fresh_exists: bool) -> str:
    chinese = language == "cn"
    title = ("## 下一阶段研究：长预算过程表现与独立随机种子复核"
             if chinese else "## Next-stage research: anytime performance and fresh-seed replication")
    lines = [title, "",
        ("这部分继续分析 **120 次真实 100k-FE 试验**，不把二次统计写成新的训练或实验次数。"
         if chinese else "New analyses of **120 actual 100k-FE runs**, not additional optimization runs."),
        ("新的研究指标为对数评价预算上的样本保持积分，衡量 10k 到 100k 的全过程误差；"
         "越低越好。均值终点和全过程排名可能不同。"
         if chinese else "New log-budget, sample-and-hold anytime loss measures the whole "
         "10k–100k trajectory; lower is better. Endpoint rankings need not match anytime rankings."),
        "",
        "![Real matched-seed convergence ribbons](docs/figures/cec2017-100k-anytime-ribbons.svg)",
        "",
        "![Paired seed endpoint comparisons](docs/figures/cec2017-100k-seed-scatter.svg)",
        "",
        ("**全过程误差：平均 log1p 误差积分**" if chinese
         else "**Anytime performance: mean integrated log1p objective error**"), "",
        ("| 函数 | ABC | EDBF | RE |" if chinese else "| Function | ABC | EDBF | RE |"),
        "|:---|---:|---:|---:|",
    ]
    idx = {(int(r["function_id"]), r["method"]): r for r in summary}
    for fid in FUNCTIONS:
        entries = [float(idx[(fid, m)]["mean_log_budget_loss"]) for m in METHODS]
        minimum = min(entries)
        formatted = [f"**{v:.4f}**" if abs(v-minimum) <= 1e-10 else f"{v:.4f}" for v in entries]
        lines.append(f"| F{fid} | "+" | ".join(formatted)+" |")
    lines += [
        "", "![Pooled 10k threshold attainment profiles](docs/figures/cec2017-100k-target-attainment.svg)",
        "", "![Paired anytime advantage and uncertainty](docs/figures/cec2017-100k-anytime-contrasts.svg)",
        "",
    ]
    if fresh_exists:
        lines += [
            ("### 全新随机种子：四函数复核（10k FE）" if chinese
             else "### Fresh-seed four-function replication (10k FE)"),
            "",
            ("本组新实验与上述已完成的 100k 轨迹分析严格分开："
             "F3/F10/F20/F30，每函数 10 个全新配对种子，三种方法，共 120 次额外真实试验。"
             if chinese else "Separately from reused 100k trajectories: F3/F10/F20/F30, "
             "10 new paired seeds/function, three methods; 120 **additional** original 10k-FE runs."),
            "",
            "![Fresh seed function replication](docs/figures/cec2017-fresh-crossfunction-ci.svg)",
            "",
            ("[原始实验与报告](docs/experiments/cec2017-fresh-functions-30d-10k-2026-10-20/report.md)"
             if chinese else "[Source trials and full report](docs/experiments/cec2017-fresh-functions-30d-10k-2026-10-20/report.md)"),
            "",
        ]
    lines += [
        ("**边界：**F16/F22 的 20 种子扩容是观察初步结果后的适应性研究，"
         "新全过程统计不等于独立确认。目标阈值来自既有 10k 样本；"
         "所有比较均应按函数、评价预算分别解释。"
         if chinese else "**Limits:** The 20-seed F16/F22 extension was adaptively chosen; "
         "anytime analysis is not independent confirmation. Target thresholds "
         "are derived from observed 10k outcomes and results must be interpreted per function and budget."),
        "",
        ("[全过程研究数据与统计报告](docs/experiments/cec2017-anytime-30d-100k-20seeds-2026-10-20/report.md)"
         if chinese else "[Anytime data, bootstrap statistics and research report]"
         "(docs/experiments/cec2017-anytime-30d-100k-20seeds-2026-10-20/report.md)"),
        "",
    ]
    return "\n".join(lines)


def patch_readme(existing: str, block: str) -> str:
    payload = FIRST + "\n" + block + "\n" + LAST
    if FIRST in existing or LAST in existing:
        if existing.count(FIRST) != 1 or existing.count(LAST) != 1:
            raise ValueError("ambiguous advanced research README section markers")
        left = existing.index(FIRST)
        right = existing.index(LAST)+len(LAST)
        return existing[:left] + payload + existing[right:]
    anchor = "<!-- BENCHMARK_RESULTS_END -->"
    if anchor not in existing:
        raise ValueError("no stable evidence section in README")
    return existing.replace(anchor, anchor + "\n\n" + payload, 1)


def emit(path: Path, payload: str, check: bool) -> bool:
    if check:
        return path.is_file() and path.read_text(encoding="utf-8") == payload
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    print(f"GENERATED {path.relative_to(ROOT)}")
    return True



def fresh_replication_svg(location: Path) -> str:
    """Four function panels from 120 additional original trials (never demo data)."""
    import json

    def csv_rows(filename: str) -> list[dict]:
        with (location / filename).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    env = json.loads((location / "environment.json").read_text(encoding="utf-8"))
    data = csv_rows("trials.csv")
    summary = csv_rows("summary.csv")
    tests = csv_rows("paired_tests.csv")
    fs = (3, 10, 20, 30)
    if (env.get("functions") != list(fs) or env.get("repeats") != 10
            or env.get("trials") != 120 or env.get("evaluations") != 10_000
            or len(data) != 120 or len(summary) != 12 or len(tests) != 8):
        raise ValueError("cannot illustrate incomplete fresh-seed replication")
    keys = {(int(r["function_id"]), int(r["repeat"]), r["method"]) for r in data}
    expected = {(fid, i, m) for fid in fs for i in range(10) for m in METHODS}
    if keys != expected:
        raise ValueError("duplicate or absent fresh-seed replication records")
    lookup = {(int(x["function_id"]), x["method"]): x for x in summary}
    for fid in fs:
        for m in METHODS:
            raw = [float(x["error"]) for x in data
                   if int(x["function_id"]) == fid and x["method"] == m]
            if not math.isclose(
                statistics.fmean(raw), float(lookup[(fid, m)]["mean_error"]), rel_tol=1e-9
            ):
                raise ValueError("fresh-seed chart cannot reconcile means with raw data")
    out = svg_start(
        1190, 755, "Independent random seeds | Four-function replication",
        "CEC2017 · 30D · 10k FE · n=10 NEW paired seeds per function · means normalized within each function",
    )
    for col, fid in enumerate(fs):
        x0, y0 = 76 + (col % 2) * 573, 175 + (col // 2) * 278
        width, height = 470, 210
        out.append(f'<rect x="{x0-20}" y="{y0-52}" width="{width+50}" '
                   f'height="{height+55}" rx="14" fill="#ffffff" stroke="#e2e8f0"/>')
        out.append(txt(x0, y0-26, f"F{fid} · fresh cohort", 20, weight="700"))
        base = min(float(lookup[(fid, m)]["mean_error"]) for m in METHODS)
        base = max(base, 1e-12)
        scores = [
            (
                float(lookup[(fid, m)]["mean_error"])/base,
                float(lookup[(fid, m)]["ci95_low"])/base,
                float(lookup[(fid, m)]["ci95_high"])/base,
            ) for m in METHODS
        ]
        top = max(1.5, max(hi for _, _, hi in scores)*1.10)
        left = x0+108
        right = x0+width-20
        xp = lambda val: left+(right-left)*math.log1p(max(val, 0))/math.log1p(top)
        for tick in (1, 2, 5, 10, 20, 50):
            if tick > top:
                continue
            xx = xp(tick)
            out.append(f'<line x1="{xx:.2f}" y1="{y0+2}" x2="{xx:.2f}" '
                       f'y2="{y0+153}" stroke="#e7ecf2"/>')
            out.append(txt(xx, y0+177, f"{tick}×", 12, anchor="middle"))
        for row, m in enumerate(METHODS):
            y = y0 + row*51+34
            mean, lo, hi = scores[row]
            out.append(txt(x0+9, y+5, m.upper(), 15, COLORS[m], weight="700"))
            out.append(f'<line x1="{xp(lo):.2f}" y1="{y}" x2="{xp(hi):.2f}" '
                       f'y2="{y}" stroke="{COLORS[m]}" stroke-width="4"/>')
            for v in (lo, hi):
                out.append(f'<line x1="{xp(v):.2f}" y1="{y-8}" '
                           f'x2="{xp(v):.2f}" y2="{y+8}" stroke="{COLORS[m]}" stroke-width="2"/>')
            out.append(f'<circle cx="{xp(mean):.2f}" cy="{y}" r="6.5" '
                       f'fill="{COLORS[m]}" stroke="white" stroke-width="1.5"/>')
            out.append(txt(xp(mean)+10, y-11, f"{mean:.2f}×", 12, COLORS[m]))
    out.append(txt(70, 734,
                   "Ratio = mean error / lowest mean within function. Whiskers are bootstrap CIs, not paired significance tests.",
                   13))
    return "\n".join(out + ["</svg>"])+"\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    indexed, traces, steps = verify()
    summary, tests, profiles = analyse(indexed, traces, steps)
    files = {
        TARGET / "anytime_summary.csv": write_csv(summary),
        TARGET / "anytime_paired.csv": write_csv(tests),
        TARGET / "target_profiles.csv": write_csv(profiles),
        TARGET / "report.md": report(summary, tests, profiles),
        FIGURES / "cec2017-100k-anytime-ribbons.svg": svg_ribbons(traces, steps),
        FIGURES / "cec2017-100k-seed-scatter.svg": svg_paired(indexed),
        FIGURES / "cec2017-100k-target-attainment.svg": svg_ecdf(profiles),
        FIGURES / "cec2017-100k-anytime-contrasts.svg": svg_auc(tests),
    }
    fresh_folder = ROOT / "docs/experiments/cec2017-fresh-functions-30d-10k-2026-10-20"
    fresh_exists = (fresh_folder / "summary.csv").is_file()
    if fresh_exists:
        files[FIGURES / "cec2017-fresh-crossfunction-ci.svg"] = fresh_replication_svg(fresh_folder)
    for language, path in (("en", ROOT / "README.md"), ("cn", ROOT / "README_CN.md")):
        files[path] = patch_readme(
            path.read_text(encoding="utf-8"),
            readme_block(language, summary, tests, fresh_exists),
        )
    errors = [str(path.relative_to(ROOT)) for path, payload in files.items()
              if not emit(path, payload, args.check)]
    if errors:
        raise SystemExit(f"Outdated study files: {', '.join(errors)}")
    print(f"Verified and analyzed {len(indexed)} original 100k trajectories; "
          f"regenerated {len(files)} data-driven artifacts.")


if __name__ == "__main__":
    main()
