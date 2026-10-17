"""Regenerate README evidence and scientific SVG figures from committed CSV files.

No simulated observations: every number comes from actual experiment artifacts.
Change configs/readme_results.json to feature a newer verified experiment.

Usage:
    python scripts/update_readme_results.py
    python scripts/update_readme_results.py --check
"""

# Ruff ISC004 is intentionally suppressed for multiline SVG/XML string assembly.
# ruff: noqa: ISC004

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/readme_results.json"
FIGURES = ROOT / "docs/figures"
START = "<!-- BENCHMARK_RESULTS_START -->"
END = "<!-- BENCHMARK_RESULTS_END -->"
METHODS = ("abc", "edbf", "re")
COLORS = {"abc": "#2563eb", "edbf": "#ea580c", "re": "#64748b"}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def parse_data() -> tuple[Path, dict, list[dict], Path]:
    settings = json.loads(CONFIG.read_text(encoding="utf-8"))
    primary = ROOT / settings["featured_experiment"]
    secondary = ROOT / settings["secondary_experiment"]
    if not primary.is_dir() or not secondary.is_dir():
        raise ValueError("configured experiment directory does not exist")
    environment = json.loads((primary / "environment.json").read_text(encoding="utf-8"))
    with (primary / "summary.csv").open(newline="", encoding="utf-8") as handle:
        summary = list(csv.DictReader(handle))
    selected = tuple(int(x) for x in environment["functions"])
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("invalid experimental function IDs")
    if len(summary) != 3 * len(selected):
        raise ValueError("summary must have all methods and functions")
    seen = set()
    for row in summary:
        fid, method = int(row["function_id"]), row["method"]
        if fid not in selected or method not in METHODS or (fid, method) in seen:
            raise ValueError("duplicate, unknown or incomplete summary row")
        seen.add((fid, method))
        for key in ("mean_error", "std_error", "mean_elapsed_seconds"):
            val = float(row[key])
            if not math.isfinite(val) or val < 0:
                raise ValueError(f"invalid {key} in function F{fid}")
        if int(row["repeats"]) != int(environment["repeats"]):
            raise ValueError("summary and environment disagree on repeat count")
        if int(float(row["mean_evaluations"])) != int(environment["evaluations"]):
            raise ValueError("summary and environment disagree on evaluation budget")
    if not (secondary / "error_comparison.png").is_file():
        raise ValueError("10D pilot figure is missing")
    return primary, environment, summary, secondary


def plot_header(title: str, subtitle: str, *, width: int = 1100) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 610" '
        f'width="{width}" height="610" role="img" aria-label="{esc(title)}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<rect x="24" y="24" width="1052" height="562" rx="18" '
        'fill="#ffffff" stroke="#dde4ee"/>',
        f'<text x="72" y="78" font-family="Arial, sans-serif" font-size="28" '
        f'font-weight="700" fill="#0f172a">{esc(title)}</text>',
        f'<text x="72" y="108" font-family="Arial, sans-serif" font-size="15" '
        f'fill="#64748b">{esc(subtitle)}</text>',
    ]


def legend() -> list[str]:
    parts = []
    for index, method in enumerate(METHODS):
        x = 685 + 122 * index
        color = COLORS[method]
        parts.extend(
            [
                f'<circle cx="{x}" cy="153" r="7" fill="{color}"/>',
                f'<text x="{x + 15}" y="158" font-family="Arial, sans-serif" '
                f'font-size="16" fill="#334155">{method.upper()}</text>',
            ]
        )
    return parts


def evidence_ratio_svg(summary: list[dict], environment: dict) -> str:
    ids = [int(x) for x in environment["functions"]]
    lookup = {(int(r["function_id"]), r["method"]): r for r in summary}
    ratios = {
        (fid, method): (
            float(lookup[(fid, method)]["mean_error"])
            / float(lookup[(fid, "re")]["mean_error"])
        )
        for fid in ids
        for method in METHODS
    }
    if any(value <= 0 or not math.isfinite(value) for value in ratios.values()):
        raise ValueError("normalization requires strictly positive finite mean errors")
    parts = plot_header(
        "CEC2017 | Objective error relative to RE",
        f'D={environment["dimension"]}  |  {environment["repeats"]} runs/method  |  '
        f'{environment["evaluations"]:,} evaluations/run  |  lower is better',
    )
    parts += legend()
    left, top, width, height = 142, 197, 864, 300
    # Scale to measured data rather than silently clipping strong gains.
    min_log = min(math.log10(value) for value in ratios.values())
    max_log = max(math.log10(value) for value in ratios.values())
    ylo = min(-2.2, math.floor(min_log) - 0.3)
    yhi = max(1.1, math.ceil(max_log) + 0.3)

    def y(value: float) -> float:
        return top + (yhi - math.log10(value)) / (yhi - ylo) * height

    for exponent in range(math.ceil(ylo), math.floor(yhi) + 1):
        tick = 10.0 ** exponent
        pos = y(tick)
        line_color = "#94a3b8" if tick == 1 else "#e2e8f0"
        thickness = 2 if tick == 1 else 1
        dash = ' stroke-dasharray="6 5"' if tick == 1 else ""
        parts.extend(
            [
                f'<line x1="{left}" y1="{pos:.2f}" x2="{left + width}" '
                f'y2="{pos:.2f}" stroke="{line_color}" stroke-width="{thickness}" '
                f'{dash}/>',
                f'<text x="{left - 22}" y="{pos + 5:.2f}" text-anchor="end" '
                f'font-family="Arial,sans-serif" font-size="14" fill="#475569">'
                f'{tick:g}x</text>',
            ]
        )

    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + height}" '
        'stroke="#94a3b8"/>'
    )
    for index, fid in enumerate(ids):
        center = left + width * (index + 0.5) / len(ids)
        parts.append(
            f'<text x="{center:.2f}" y="{top + height + 36}" text-anchor="middle" '
            f'font-family="Arial,sans-serif" font-size="19" font-weight="600" '
            f'fill="#334155">F{fid}</text>'
        )
        for offset, method in zip((-35, 0, 35), METHODS):
            x = center + offset
            value = ratios[(fid, method)]
            if not ylo <= math.log10(value) <= yhi:
                raise ValueError(f"ratio outside plotted range: F{fid} {method}={value}")
            pos = y(value)
            parts.extend(
                [
                    f'<line x1="{x:.2f}" y1="{pos:.2f}" x2="{x:.2f}" '
                    f'y2="{y(1):.2f}" stroke="{COLORS[method]}" '
                    'stroke-width="1.5" opacity="0.26"/>',
                    f'<circle cx="{x:.2f}" cy="{pos:.2f}" r="10" '
                    f'fill="{COLORS[method]}" stroke="white" stroke-width="2"/>',
                    f'<title>F{fid}, {method.upper()}, ratio={value:.5g}</title>',
                ]
            )

    parts.append(
        '<text x="142" y="559" font-family="Arial,sans-serif" '
        'font-size="14" fill="#64748b">'
        'Ratio = method mean error / RE mean error; 1x = RE reference; log scale</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def runtime_svg(summary: list[dict], environment: dict) -> str:
    ids = [int(x) for x in environment["functions"]]
    lookup = {(int(row["function_id"]), row["method"]): row for row in summary}
    parts = plot_header(
        "CEC2017 | Measured runtime per trial",
        f'D={environment["dimension"]}  |  {environment["repeats"]} runs/method  |  '
        f'{environment["evaluations"]:,} evaluations/run  |  lower is better',
    )
    parts += legend()
    left, top, width, height = 142, 198, 864, 298
    values = [float(row["mean_elapsed_seconds"]) for row in summary]
    axis_max = max(1.0, math.ceil(max(values) * 1.18))
    for tick in range(int(axis_max) + 1):
        pos = top + height * (1 - tick / axis_max)
        parts.extend(
            [
                f'<line x1="{left}" y1="{pos:.2f}" x2="{left + width}" '
                f'y2="{pos:.2f}" stroke="#e2e8f0"/>',
                f'<text x="{left - 22}" y="{pos + 5:.2f}" text-anchor="end" '
                f'font-family="Arial,sans-serif" font-size="14" fill="#475569">'
                f'{tick}s</text>',
            ]
        )
    bar_w = 44 if len(ids) <= 4 else 30
    for index, fid in enumerate(ids):
        center = left + width * (index + 0.5) / len(ids)
        parts.append(
            f'<text x="{center:.2f}" y="{top + height + 36}" text-anchor="middle" '
            f'font-family="Arial,sans-serif" font-size="19" font-weight="600" '
            f'fill="#334155">F{fid}</text>'
        )
        for offset, method in zip((-1, 0, 1), METHODS):
            value = float(lookup[(fid, method)]["mean_elapsed_seconds"])
            h = height * value / axis_max
            x = center + offset * (bar_w + 6) - bar_w / 2
            y = top + height - h
            parts.extend(
                [
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w}" '
                    f'height="{h:.2f}" rx="4" fill="{COLORS[method]}"/>',
                    f'<text x="{x + bar_w / 2:.2f}" y="{y - 8:.2f}" '
                    'font-family="Arial,sans-serif" text-anchor="middle" '
                    f'font-size="12" fill="#334155">{value:.2f}</text>',
                ]
            )

    parts.append(
        '<text x="142" y="559" font-family="Arial,sans-serif" '
        'font-size="14" fill="#64748b">'
        'Wall-clock seconds on the GitHub Actions runner; not hardware-normalized</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def fmt_error(value: float) -> str:
    if value >= 1_000_000:
        return f"{value:.3e}"
    return f"{value:,.1f}"


def section(primary: Path, secondary: Path, env: dict, summary: list[dict], lang: str) -> str:
    rel = primary.relative_to(ROOT).as_posix()
    pilot = secondary.relative_to(ROOT).as_posix()
    by_id = {(int(row["function_id"]), row["method"]): row for row in summary}
    functions = [int(fid) for fid in env["functions"]]
    en = lang == "en"
    heading = "Measured CEC2017 results — 30D" if en else "真实 CEC2017 实验结果（30 维）"
    intro = (
        f"**Real runs, not simulated:** D={env['dimension']}, "
        f"{env['evaluations']:,} function evaluations per run, "
        f"{env['repeats']} paired initial seeds per method, "
        f"{len(functions) * 3 * env['repeats']} independent optimization trials. "
        "ABC, EDBF, and RE share the same initial population for each "
        "function/repetition pair."
        if en
        else f"**以下均为真实运行数据，而非模拟结果。** D={env['dimension']}，"
        f"每次 {env['evaluations']:,} 次函数评价，每种方法 {env['repeats']} 个配对初始种子，"
        f"共 {len(functions) * 3 * env['repeats']} 次独立优化试验。"
        "同一函数及重复编号下，ABC、EDBF、RE 具有相同的初始化种群。"
    )
    lines = [
        f"## {heading}",
        "",
        intro,
        "",
        "![CEC2017 30D normalized objective error](docs/figures/cec2017-30d-relative-error.svg)",
        "",
        "![CEC2017 30D runtime comparison](docs/figures/cec2017-30d-runtime.svg)",
        "",
        ("**Mean final objective error (lower is better)**" if en else "**最终平均目标误差（越低越好）**"),
        "",
        "| Function | ABC | EDBF | RE |" if en else "| 测试函数 | ABC | EDBF | RE |",
        "|:---|---:|---:|---:|",
    ]
    for fid in functions:
        errors = {method: float(by_id[(fid, method)]["mean_error"]) for method in METHODS}
        best = min(errors.values())
        nums = [
            f"**{fmt_error(errors[method])}**"
            if math.isclose(errors[method], best, rel_tol=1e-12)
            else fmt_error(errors[method])
            for method in METHODS
        ]
        lines.append(f"| F{fid} | {' | '.join(nums)} |")
    lines += [
        "",
        (
            f"Source: [raw trials]({rel}/trials.csv) · "
            f"[mean and SD]({rel}/summary.csv) · "
            f"[paired tests]({rel}/paired_sign_tests.csv) · "
            f"[environment]({rel}/environment.json) · "
            f"[full analysis]({rel}/statistical_analysis_CN.md)"
            if en
            else f"实验来源：[120 次原始记录]({rel}/trials.csv) · "
            f"[均值/标准差]({rel}/summary.csv) · "
            f"[配对检验]({rel}/paired_sign_tests.csv) · "
            f"[环境记录]({rel}/environment.json) · "
            f"[中文分析报告]({rel}/statistical_analysis_CN.md)"
        ),
        "",
        (
            "**Interpretation:** ABC has the lowest mean error on F1, F3, and F30; "
            "**EDBF is slightly better on F10**. These exploratory results do not "
            "establish universal superiority. The C-derived Python benchmark "
            "is an independent reference, not the original official C binary. "
            "The 58/58 finite/optimum preflight checks were sampled-point checks, "
            "not exhaustive validation. The 3,000-evaluation budget is much "
            "smaller than a full paper-level experiment."
            if en
            else "**解释边界：**ABC 在 F1、F3、F30 的平均误差最低，"
            "**F10 则由 EDBF 略优**。这只能说明当前所测函数与预算下的表现，"
            "不能推导出对全部函数的普遍优势。独立 Python 后端并非原始官方 C 程序；"
            "58/58 项仅为有限采样点的数值预检，且每次 3,000 次评价不等于论文级完整复现。"
        ),
        "",
        (
            "<details><summary>Earlier 10D exploratory pilot (different backend; "
            "do not pool results)</summary>"
            if en
            else "<details><summary>更早的 10 维探索性实验（使用另一后端，数据不得混合统计）</summary>"
        ),
        "",
        f"![Earlier 10D pilot]({pilot}/error_comparison.png)",
        "",
        (
            f"[Pilot raw CSV]({pilot}/validation_trials.csv) · "
            f"[pilot report]({pilot}/validation_readme.md)"
            if en
            else f"[10 维原始数据]({pilot}/validation_trials.csv) · "
            f"[试验说明]({pilot}/validation_readme.md)"
        ),
        "",
        "</details>",
    ]
    return "\n".join(lines)




def load_screening() -> tuple[Path, dict, list[dict]] | None:
    """Return an optional complete-suite screening after its CSV is published."""

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    dirname = config.get("screen_experiment")
    if not dirname:
        return None
    folder = ROOT / dirname
    if not (folder / "summary.csv").exists():
        # The full screening may still be running on GitHub Actions.
        return None
    environment = json.loads((folder / "environment.json").read_text(encoding="utf-8"))
    with (folder / "summary.csv").open(newline="", encoding="utf-8") as handle:
        data = list(csv.DictReader(handle))
    ids = [int(item) for item in environment["functions"]]
    if len(ids) != 29 or set(ids) != ({1} | set(range(3, 31))):
        raise ValueError("screening must contain all 29 official CEC2017 functions")
    if len(data) != len(ids) * len(METHODS):
        raise ValueError("screening result table has incomplete method coverage")
    found = set()
    for row in data:
        key = (int(row["function_id"]), row["method"])
        error = float(row["mean_error"])
        if key in found or key[0] not in ids or key[1] not in METHODS:
            raise ValueError("screening includes unknown or duplicate cases")
        if not math.isfinite(error) or error < 0:
            raise ValueError("screening contains an invalid mean objective error")
        if int(row["repeats"]) != int(environment["repeats"]):
            raise ValueError("screening metadata disagree about repeat count")
        found.add(key)
    return folder, environment, data


def screen_winners(
    environment: dict, summary: list[dict]
) -> tuple[list[tuple[int, str]], dict[str, int]]:
    lookup = {(int(row["function_id"]), row["method"]): row for row in summary}
    winners = []
    counts = {method: 0 for method in METHODS}
    counts["tie"] = 0
    for fid in [int(x) for x in environment["functions"]]:
        scores = {method: float(lookup[(fid, method)]["mean_error"]) for method in METHODS}
        minimum = min(scores.values())
        leader = [
            method for method, value in scores.items()
            if math.isclose(value, minimum, rel_tol=1e-12, abs_tol=1e-12)
        ]
        selected = leader[0] if len(leader) == 1 else "tie"
        counts[selected] += 1
        winners.append((fid, selected))
    return winners, counts


def screening_svg(environment: dict, data: list[dict]) -> str:
    winners, counts = screen_winners(environment, data)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 580" '
        'width="1100" height="580" role="img" '
        'aria-label="CEC2017 29 function screening lowest mean error by function">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<rect x="24" y="24" width="1052" height="532" rx="18" '
        'fill="#ffffff" stroke="#dde4ee"/>',
        '<text x="72" y="80" font-family="Arial,sans-serif" font-size="28" '
        'font-weight="700" fill="#0f172a">CEC2017 | 29-function screening</text>',
        (
            f'<text x="72" y="111" font-family="Arial,sans-serif" font-size="15" '
            f'fill="#64748b">D={environment["dimension"]}; '
            f'{environment["repeats"]} paired seeds/method; '
            f'{environment["evaluations"]:,} evaluations/run; exploratory</text>'
        ),
        '<text x="72" y="171" font-family="Arial,sans-serif" font-size="19" '
        'font-weight="600" fill="#334155">Lowest observed mean error per function</text>',
    ]
    palette = {**COLORS, "tie": "#64748b"}
    for idx, method in enumerate((*METHODS, "tie")):
        x = 510 + 135 * idx
        color = palette[method]
        parts.extend(
            [
                f'<rect x="{x}" y="149" width="18" height="18" rx="4" '
                f'fill="{color}"/>',
                f'<text x="{x + 25}" y="163" font-family="Arial,sans-serif" '
                f'font-size="15" fill="#334155">{method.upper()}</text>',
            ]
        )
    for index, (fid, method) in enumerate(winners):
        x = 75 + index * 34
        parts.extend(
            [
                f'<rect x="{x}" y="208" width="29" height="49" rx="4" '
                f'fill="{palette[method]}"/>',
                f'<text x="{x + 14.5:.1f}" y="279" font-family="Arial,sans-serif" '
                'font-size="11" fill="#475569" text-anchor="middle">'
                f'F{fid}</text>',
            ]
        )
    parts.extend(
        [
            '<text x="72" y="342" font-family="Arial,sans-serif" font-size="19" '
            'font-weight="600" fill="#334155">Functions led (by mean only)</text>',
        ]
    )
    for index, method in enumerate(METHODS):
        x = 95 + 336 * index
        y = 390
        share = counts[method] / len(winners)
        width = 242 * share
        parts.extend(
            [
                f'<text x="{x}" y="{y - 10}" font-family="Arial,sans-serif" '
                f'font-size="16" fill="#334155">{method.upper()} — '
                f'{counts[method]} / {len(winners)}</text>',
                f'<rect x="{x}" y="{y + 5}" width="242" height="27" '
                'rx="6" fill="#e2e8f0"/>',
                f'<rect x="{x}" y="{y + 5}" width="{width:.2f}" height="27" '
                f'rx="6" fill="{palette[method]}"/>',
            ]
        )
    parts.extend(
        [
            '<text x="72" y="505" font-family="Arial,sans-serif" font-size="14" '
            'fill="#64748b">Short-budget screening, not a significance test. '
            'Do not pool with the 3,000-evaluation pilot.</text>',
            '</svg>',
        ]
    )
    return "\n".join(parts) + "\n"


def screening_markdown(folder: Path, environment: dict, data: list[dict], lang: str) -> str:
    winners, counts = screen_winners(environment, data)
    root = folder.relative_to(ROOT).as_posix()
    en = lang == "en"
    title = (
        "### All 29 functions: exploratory 30D screening"
        if en else "### 全部 29 个函数：30 维探索性普查"
    )
    intro = (
        f"**{len(winners) * 3 * environment['repeats']} real trials** with "
        f"{environment['repeats']} matched seeds per method and "
        f"{environment['evaluations']:,} evaluations per trial. "
        "The figure colors indicate the lowest *observed mean* error, not "
        "statistically established winners."
        if en else
        f"共 **{len(winners) * 3 * environment['repeats']} 次真实试验**；"
        f"每种方法 {environment['repeats']} 个配对种子、"
        f"每次 {environment['evaluations']:,} 次函数评价。"
        "颜色只表示观测均值最低，并不表示统计显著。"
    )
    lead = (
        "Functions with the lowest observed average error: "
        if en else "获得最低观测平均误差的函数数量："
    )
    return "\n".join(
        [
            title,
            "",
            intro,
            "",
            "![CEC2017 all 29 functions screening winner map]"
            "(docs/figures/cec2017-30d-29function-screen.svg)",
            "",
            lead + ", ".join(f"{m.upper()} {counts[m]}" for m in METHODS)
            + (f", ties {counts['tie']}" if counts["tie"] else "") + ".",
            "",
            (
                f"[Full screening CSV]({root}/trials.csv) · "
                f"[per-function means]({root}/summary.csv) · "
                f"[environment]({root}/environment.json) · "
                f"[Chinese analysis]({root}/statistical_analysis_CN.md)"
                if en else
                f"[261 条原始记录]({root}/trials.csv) · "
                f"[逐函数均值]({root}/summary.csv) · "
                f"[实验环境]({root}/environment.json) · "
                f"[中文结果分析]({root}/statistical_analysis_CN.md)"
            ),
            "",
            (
                "**Budget caveat:** This 1,200-evaluation screening must not be "
                "pooled with the 3,000-evaluation main result."
                if en else
                "**预算限制：**本轮 1,200 次评价的普查结果不得与前述 "
                "3,000 次评价的实验合并统计。"
            ),
        ]
    )




def load_long_budget() -> tuple[Path, dict, list[dict], list[dict]] | None:
    """Load and independently validate every trial before showing a 10k-FE result."""

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    directory = config.get("long_budget_experiment")
    if not directory:
        return None
    folder = ROOT / directory
    if not (folder / "summary.csv").is_file():
        return None
    environment = json.loads((folder / "environment.json").read_text(encoding="utf-8"))
    ids = [int(fid) for fid in environment["functions"]]
    reps = int(environment["repeats"])
    budget = int(environment["evaluations"])
    if (ids, int(environment["dimension"]), reps, budget) != (
        [10, 20, 22, 30], 30, 10, 10_000
    ):
        raise ValueError("long-budget experiment metadata do not match protocol")
    with (folder / "summary.csv").open(newline="", encoding="utf-8") as handle:
        summary = list(csv.DictReader(handle))
    if len(summary) != len(ids) * len(METHODS):
        raise ValueError("long-budget summary is incomplete")
    summary_keys = set()
    for row in summary:
        key = (int(row["function_id"]), row["method"])
        if key in summary_keys or key[0] not in ids or key[1] not in METHODS:
            raise ValueError("duplicate or unexpected long-budget summary")
        summary_keys.add(key)
        if int(row["repeats"]) != reps or int(float(row["mean_evaluations"])) != budget:
            raise ValueError("long-budget summary has incorrect repetitions or budget")
        for column in ("mean_error", "std_error", "mean_elapsed_seconds"):
            value = float(row[column])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"invalid long-budget {column}: {key}")
    with (folder / "trials.csv").open(newline="", encoding="utf-8") as handle:
        trials = list(csv.DictReader(handle))
    if len(trials) != len(ids) * len(METHODS) * reps:
        raise ValueError("long-budget trial CSV has missing observations")
    grouped: dict[tuple[int, int], list[dict]] = {}
    for row in trials:
        fid = int(row["function_id"])
        rep = int(row["repeat"])
        if fid not in ids or not 0 <= rep < reps:
            raise ValueError("unexpected function or repetition in long-budget trials")
        if int(row["evaluations"]) != budget or int(row["dimension"]) != 30:
            raise ValueError("incorrect budget or dimension in long-budget trial")
        if not math.isfinite(float(row["error"])) or float(row["error"]) < 0:
            raise ValueError("nonfinite or negative objective error")
        grouped.setdefault((fid, rep), []).append(row)
    if len(grouped) != len(ids) * reps:
        raise ValueError("long-budget trials contain incomplete paired groups")
    for (fid, rep), matched in grouped.items():
        if len(matched) != len(METHODS):
            raise ValueError(f"duplicate/missing method for F{fid} repeat {rep}")
        if {row["method"] for row in matched} != set(METHODS):
            raise ValueError(f"missing method for F{fid} repeat {rep}")
        if len({row["seed"] for row in matched}) != 1:
            raise ValueError(f"unpaired seeds for F{fid} repeat {rep}")
    for entry in summary:
        subset = [
            float(row["error"]) for row in trials
            if int(row["function_id"]) == int(entry["function_id"])
            and row["method"] == entry["method"]
        ]
        if len(subset) != reps or not math.isclose(
            statistics.fmean(subset), float(entry["mean_error"]), rel_tol=1e-10
        ):
            raise ValueError("long-budget summary does not match raw trial CSV")
    return folder, environment, summary, trials






def budget_progress_svg(
    prior_summary: list[dict], long_summary: list[dict],
    prior_environment: dict, long_environment: dict
) -> str:
    """Plot 10k/3k mean-error ratios on overlapping functions only."""

    previous = {(int(row["function_id"]), row["method"]): row for row in prior_summary}
    current = {(int(row["function_id"]), row["method"]): row for row in long_summary}
    functions = sorted(set(prior_environment["functions"]) & set(long_environment["functions"]))
    if functions != [10, 30]:
        raise ValueError("budget sensitivity chart expects F10 and F30")
    if prior_environment["dimension"] != long_environment["dimension"]:
        raise ValueError("budget sensitivity requires identical dimensions")
    if int(prior_environment["repeats"]) != int(long_environment["repeats"]):
        raise ValueError("budget sensitivity requires identical repeat counts")
    ratios = {}
    for fid in functions:
        for method in METHODS:
            original = float(previous[(fid, method)]["mean_error"])
            later = float(current[(fid, method)]["mean_error"])
            if original <= 0 or not math.isfinite(original) or not math.isfinite(later):
                raise ValueError("budget sensitivity needs finite positive baseline error")
            ratios[(fid, method)] = later / original
    top, height = 207, 270
    max_ratio = max(1.0, max(ratios.values()))
    upper = max(1.2, max_ratio * 1.15)
    parts = plot_header(
        "CEC2017 | Evaluation-budget sensitivity",
        "F10 / F30 only | Mean error relative to each method at 3,000 FEs | lower is better"
    )
    parts += legend()

    def y(value: float) -> float:
        return top + height * (1.0 - value / upper)

    for t in range(6):
        tick = upper * t / 5
        yy = y(tick)
        parts.extend(
            [
                (
                    f'<line x1="125" y1="{yy:.2f}" x2="1012" y2="{yy:.2f}" '
                    'stroke="#e2e8f0"/>'
                ),
                (
                    f'<text x="107" y="{yy + 5:.2f}" font-family="Arial,sans-serif" '
                    f'font-size="14" text-anchor="end" fill="#64748b">{tick:.2f}x</text>'
                ),
            ]
        )
    for index, fid in enumerate(functions):
        center = 342 + index * 424
        x0, x1 = center - 115, center + 115
        parts.extend(
            [
                (
                    f'<text x="{center}" y="534" font-family="Arial,sans-serif" '
                    f'font-size="21" text-anchor="middle" font-weight="700" '
                    f'fill="#334155">F{fid}</text>'
                ),
                (
                    f'<text x="{x0}" y="503" font-family="Arial,sans-serif" '
                    f'font-size="15" text-anchor="middle" fill="#64748b">3k</text>'
                ),
                (
                    f'<text x="{x1}" y="503" font-family="Arial,sans-serif" '
                    f'font-size="15" text-anchor="middle" fill="#64748b">10k</text>'
                ),
            ]
        )
        for method in METHODS:
            y0 = y(1.0)
            y1 = y(ratios[(fid, method)])
            parts.extend(
                [
                    (
                        f'<line x1="{x0}" y1="{y0:.2f}" x2="{x1}" y2="{y1:.2f}" '
                        f'stroke="{COLORS[method]}" stroke-width="4"/>'
                    ),
                    (
                        f'<circle cx="{x0}" cy="{y0:.2f}" r="7" '
                        f'fill="{COLORS[method]}" stroke="white" stroke-width="1"/>'
                    ),
                    (
                        f'<circle cx="{x1}" cy="{y1:.2f}" r="7" '
                        f'fill="{COLORS[method]}" stroke="white" stroke-width="1"/>'
                    ),
                    (
                        f'<title>F{fid}, {method}: 10k/3k mean error '
                        f'{ratios[(fid, method)]:.6g}</title>'
                    ),
                ]
            )
    parts.extend(
        [
            '<text x="125" y="572" font-family="Arial,sans-serif" font-size="14" '
            'fill="#64748b">Budget cohorts are reported separately; '
            'a lower ratio means greater error reduction.</text>',
            '</svg>',
        ]
    )
    return "\n".join(parts) + "\n"


def longbudget_paired_sign_holm(
    environment: dict, trials: list[dict]
) -> list[dict]:
    """Exact two-sided sign tests with Holm family-wise adjustment."""

    by_key = {
        (int(row["function_id"]), int(row["repeat"]), row["method"]):
        float(row["error"])
        for row in trials
    }
    hypotheses = []
    for fid in environment["functions"]:
        for baseline in ("edbf", "re"):
            wins = 0
            losses = 0
            ties = 0
            for rep in range(int(environment["repeats"])):
                gap = by_key[(fid, rep, baseline)] - by_key[(fid, rep, "abc")]
                if gap > 1e-10:
                    wins += 1
                elif gap < -1e-10:
                    losses += 1
                else:
                    ties += 1
            n = wins + losses
            shorter = min(wins, losses)
            p = (
                min(1.0, 2 * sum(math.comb(n, k) for k in range(shorter + 1)) / 2**n)
                if n > 0 else 1.0
            )
            hypotheses.append(
                {"function_id": fid, "baseline": baseline,
                 "wins": wins, "losses": losses, "ties": ties,
                 "p_raw": p, "p_holm": 1.0}
            )
    order = sorted(range(len(hypotheses)), key=lambda i: hypotheses[i]["p_raw"])
    cumulative = 0.0
    for rank, index in enumerate(order):
        adjusted = min(1.0, hypotheses[index]["p_raw"] * (len(order) - rank))
        cumulative = max(cumulative, adjusted)
        hypotheses[index]["p_holm"] = cumulative
    return hypotheses


def longbudget_markdown(
    folder: Path,
    environment: dict,
    summary: list[dict],
    trials: list[dict],
    lang: str,
    prior_environment: dict,
    prior_summary: list[dict],
) -> str:
    """Render longer-budget evidence and compare common cases across budgets."""

    en = lang == "en"
    loc = folder.relative_to(ROOT).as_posix()
    for key in ("reference_commit", "base_seed"):
        if environment.get(key) != prior_environment.get(key):
            raise ValueError(f"cross-budget comparison requires equal {key}")
    by_case = {(int(row["function_id"]), row["method"]): row for row in summary}
    prior = {(int(row["function_id"]), row["method"]): row for row in prior_summary}
    title = (
        "### Higher-budget verification: 10,000 evaluations"
        if en else "### 高评价预算验证：每次 10,000 次函数评价"
    )
    header = (
        "**120 measured trials** at D=30 (F10, F20, F22, F30), "
        "10 matched initial seeds/method. The focus includes the cases "
        "where ABC did not lead in earlier experiments."
        if en else
        "**120 次真实试验**，D=30，测试 F10、F20、F22、F30，"
        "每方法 10 个配对初始种子。重点检验此前 ABC 未领先的函数。"
    )
    rows = [
        title,
        "",
        header,
        "",
        "![10k-FE error ratio compared to RE]"
        "(docs/figures/cec2017-30d-longbudget-relative-error.svg)",
        "",
        "![3k vs 10k evaluation-budget progression on F10 and F30]"
        "(docs/figures/cec2017-30d-budget-progression.svg)",
        "",
        "| Function | ABC | EDBF | RE |" if en else "| 函数 | ABC | EDBF | RE |",
        "|:---|---:|---:|---:|",
    ]
    for fid in environment["functions"]:
        scores = {method: float(by_case[(fid, method)]["mean_error"]) for method in METHODS}
        best = min(scores.values())
        rendered = [
            f"**{fmt_error(scores[method])}**"
            if math.isclose(scores[method], best, rel_tol=1e-12)
            else fmt_error(scores[method])
            for method in METHODS
        ]
        rows.append(f"| F{fid} | {' | '.join(rendered)} |")
    matched_fids = sorted(set(environment["functions"]) & set(prior_environment["functions"]))
    if int(prior_environment["evaluations"]) != 3_000:
        raise ValueError("cross-budget comparison expects 3000-FE baseline")
    if int(prior_environment["repeats"]) != int(environment["repeats"]):
        raise ValueError("cross-budget comparison requires matched repeats")
    rows.extend(
        [
            "",
            (
                f"**Cross-budget check** (same reference-derived backend and "
                f"seed schedule; {prior_environment['evaluations']:,} → "
                f"{environment['evaluations']:,} evaluations):"
                if en else
                f"**跨预算验证**（同一参考后端与种子规则，"
                f"{prior_environment['evaluations']:,} → "
                f"{environment['evaluations']:,} 次评价）："
            ),
            "",
            "| Function | Method | 3k FE mean error | 10k FE mean error |"
            if en else "| 函数 | 方法 | 3k 次评价误差 | 10k 次评价误差 |",
            "|:---|:---|---:|---:|",
        ]
    )
    for fid in matched_fids:
        for method in METHODS:
            previous = float(prior[(fid, method)]["mean_error"])
            current = float(by_case[(fid, method)]["mean_error"])
            rows.append(f"| F{fid} | {method.upper()} | {fmt_error(previous)} | {fmt_error(current)} |")
    raw = {(int(r["function_id"]), int(r["repeat"]), r["method"]): float(r["error"]) for r in trials}
    total_wins: dict[str, int] = {method: 0 for method in METHODS}
    for fid in environment["functions"]:
        for method in ("edbf", "re"):
            for rep in range(int(environment["repeats"])):
                if raw[(fid, rep, "abc")] < raw[(fid, rep, method)]:
                    total_wins[method] += 1
    tests = longbudget_paired_sign_holm(environment, trials)
    rows.extend(
        [
            "",
            (
                "**Exact paired sign tests with Holm correction across 8 comparisons** "
                "(exploratory; lower error is better):"
                if en else
                "**配对精确符号检验（全部 8 项统一 Holm 校正，仅探索性）：**"
            ),
            "",
            "| Function | Contrast | ABC W/L/T | Raw p | Holm p |"
            if en else "| 函数 | 对照 | ABC 胜/负/平 | 原始 p | Holm 校正 p |",
            "|:---|:---|---:|---:|---:|",
        ]
    )
    for test in tests:
        rows.append(
            f"| F{test['function_id']} | ABC vs {test['baseline'].upper()} | "
            f"{test['wins']}/{test['losses']}/{test['ties']} | "
            f"{test['p_raw']:.5g} | {test['p_holm']:.5g} |"
        )
    rows.extend(
        [
            "",
            (
                "Paired wins by ABC across the 40 matched seeds in the four "
                "functions (ties not counted): "
                if en else
                "四个函数共 40 组配对种子中 ABC 的获胜次数（不计平局）："
            ) + f"vs EDBF {total_wins['edbf']}/40; vs RE {total_wins['re']}/40.",
            "",
            (
                f"[Raw 120 trials]({loc}/trials.csv) · "
                f"[summary]({loc}/summary.csv) · "
                f"[paired tests]({loc}/paired_sign_tests.csv) · "
                f"[environment]({loc}/environment.json) · "
                f"[Chinese analysis]({loc}/statistical_analysis_CN.md)"
                if en else
                f"[120 次原始试验]({loc}/trials.csv) · "
                f"[均值和方差]({loc}/summary.csv) · "
                f"[配对检验]({loc}/paired_sign_tests.csv) · "
                f"[环境记录]({loc}/environment.json) · "
                f"[中文分析报告]({loc}/statistical_analysis_CN.md)"
            ),
            "",
            (
                "**Limitations:** This is a selected-function challenge, not "
                "a 29-function 10k-FE suite. Runtime differences and different "
                "budget lengths must not be pooled. Mean leads alone do not "
                "establish significance."
                if en else
                "**解释边界：**这只是选定四函数的高预算试验，不是完整 29 函数的 "
                "10k 次评价复现。不同预算不能合并统计，均值领先不等于显著优势。"
            ),
        ]
    )
    return "\n".join(rows)




def longbudget_analysis_cn(
    folder: Path, env: dict, summary: list[dict], trials: list[dict],
    prior_env: dict, prior_summary: list[dict],
) -> str:
    """Generate a Chinese scientific report entirely from measured CSV records."""

    result_map = {(int(row["function_id"]), row["method"]): row for row in summary}
    previous = {(int(row["function_id"]), row["method"]): row for row in prior_summary}
    methods = ("abc", "edbf", "re")
    tests = longbudget_paired_sign_holm(env, trials)
    lines = [
        "# BoundEvo：CEC2017 高评价预算配对实验分析", "",
        "## 实验方法", "",
        f"- 后端：{env['reference_repo']}；固定修订版 "
        f"`{env['reference_commit']}`。",
        f"- 目标函数：{', '.join('F'+str(fid) for fid in env['functions'])}；"
        f"维度 D={env['dimension']}。",
        f"- 每种方法重复 {env['repeats']} 次，"
        f"每次 {env['evaluations']:,} 次函数评价，共 {len(trials)} 条实测记录。",
        "- 优化器采用 N=100、M=15、K=5、L=1，ABC、EDBF、RE "
        "在同一函数和重复编号使用相同初始种子。",
        "- 该实验刻意包含前期表现存在争议的 F10、F20、F22，"
        "并包含 F30 作为对照函数。",
        "- 代码和运行环境请以 [environment.json](environment.json) 为准。",
        "", "## 原始测量汇总", "",
        "| 函数 | 方法 | 均值误差 | 误差标准差 | 平均耗时(s) | 生成候选数/子代 |",
        "|:---|:---|---:|---:|---:|---:|",
    ]
    for fid in env["functions"]:
        for method in methods:
            row = result_map[(fid, method)]
            lines.append(
                f"| F{fid} | {method.upper()} | {float(row['mean_error']):.6g} | "
                f"{float(row['std_error']):.6g} | "
                f"{float(row['mean_elapsed_seconds']):.3f} | "
                f"{float(row['mean_attempts_per_offspring']):.2f} |"
            )
    lines += [
        "", "## 逐函数配对精确符号检验与 Holm 校正", "",
        "每个函数共有 10 个配对种子，比较方向为“对照误差 − ABC 误差”。"
        "其中胜表示 ABC 误差较小。四个函数与两个对照算法组成 8 个检验，"
        "按 Holm 方法统一调整。",
        "",
        "| 函数 | 对照 | ABC 胜/负/平 | 双侧原始 p | Holm p |",
        "|:---|:---|---:|---:|---:|",
    ]
    for test in tests:
        lines.append(
            f"| F{test['function_id']} | {test['baseline'].upper()} | "
            f"{test['wins']}/{test['losses']}/{test['ties']} | "
            f"{test['p_raw']:.6g} | {test['p_holm']:.6g} |"
        )
    lines += [
        "", "## 3,000 与 10,000 次函数评价的可比子集", "",
        "仅 F10 与 F30 在此前 3,000 次评价实验中存在同后端、"
        "同随机种子编号和同维度的记录。"
        "这一比较是描述性的，不将不同预算下的数据混入同一个总体均值。",
        "",
        "| 函数 | 方法 | 3k 平均误差 | 10k 平均误差 | 相对变化 |",
        "|:---|:---|---:|---:|---:|",
    ]
    shared = sorted(set(env["functions"]) & set(prior_env["functions"]))
    for fid in shared:
        for method in methods:
            before = float(previous[(fid, method)]["mean_error"])
            after = float(result_map[(fid, method)]["mean_error"])
            fraction = (after / before - 1) * 100 if before > 0 else float("nan")
            lines.append(
                f"| F{fid} | {method.upper()} | {before:.6g} | "
                f"{after:.6g} | {fraction:+.2f}% |"
            )
    leaders = {}
    for fid in env["functions"]:
        leaders[fid] = min(
            methods, key=lambda m: float(result_map[(fid, m)]["mean_error"])
        )
    lines += [
        "", "## 研究结论的限定范围", "",
        "本轮各函数最低观测均值来自：" +
        "；".join(f"F{fid}—{method.upper()}" for fid, method in leaders.items()) + "。",
        "配对显著性应按上表 Holm 调整后的结果判断；"
        "不能仅据均值差距宣称统计显著。",
        "本轮仅覆盖 4 个经过有目的挑选的函数，"
        "可能存在选择效应，不能将结论推广为 29 函数整体性能。",
        "Wall-clock 时间取自 GitHub Actions runner，"
        "不能作为跨机器、跨实现的普适加速比。",
        "所用后端是独立的参考衍生 Python 实现，不等同于主办方原始 C 二进制。",
        "后续仍需更高预算、完整函数集与更多独立重复。",
        "", "## 可追溯文件", "",
        "- [120 条原始数据](trials.csv)",
        "- [统计汇总](summary.csv)",
        "- [未校正的原始配对符号检验](paired_sign_tests.csv)",
        "- [后端数值预检](backend_preflight.csv)",
        "- [环境、种子及固定上游源码](environment.json)",
        "",
    ]
    return "\n".join(lines)




def load_full_suite() -> tuple[Path, dict, list[dict], list[dict], list[dict]] | None:
    """Read real all-29-function results only after their aggregator has validated them."""

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    folder_name = config.get("full_suite_experiment")
    if not folder_name:
        return None
    folder = ROOT / folder_name
    if not (folder / "summary.csv").is_file():
        return None
    env = json.loads((folder / "environment.json").read_text(encoding="utf-8"))
    ids = [int(x) for x in env["functions"]]
    if (
        len(ids) != 29 or set(ids) != ({1} | set(range(3, 31)))
        or int(env["dimension"]) != 30
        or int(env["evaluations"]) != 10000
        or int(env["repeats"]) != 3
        or int(env["trials"]) != 261
        or env["reference_commit"] != "424a9fa2757914c3e4cfdd8f59a268b1aeb3197f"
    ):
        raise ValueError("unverified 29-function full-suite protocol")
    with (folder / "summary.csv").open(newline="", encoding="utf-8") as handle:
        summary = list(csv.DictReader(handle))
    with (folder / "history.csv").open(newline="", encoding="utf-8") as handle:
        history = list(csv.DictReader(handle))
    with (folder / "paired_function_tests.csv").open(newline="", encoding="utf-8") as handle:
        tests = list(csv.DictReader(handle))
    if len(summary) != 87 or len(history) != int(env["convergence_rows"]) or len(tests) != 2:
        raise ValueError("incomplete full-suite summary, history, or statistical analysis")
    pairs = {(int(row["function_id"]), row["method"]) for row in summary}
    if pairs != {(fid, method) for fid in ids for method in METHODS}:
        raise ValueError("invalid full-suite function and method coverage")
    for row in summary:
        if (
            int(row["repeats"]) != 3
            or int(float(row["mean_evaluations"])) != 10000
            or not math.isfinite(float(row["mean_error"]))
            or float(row["mean_error"]) < 0
        ):
            raise ValueError("invalid full-suite mean summary")
    return folder, env, summary, history, tests


def fullsuite_convergence_svg(history: list[dict], env: dict) -> str:
    """Four real convergence comparisons, grouped by function and method.

    Each curve divides its mean checkpoint error by the same method's mean
    initial error for that function. This permits showing different functions
    on a common relative scale without averaging their raw objective values.
    """

    selected = (10, 20, 22, 30)
    by_case: dict[tuple[int, str, int], list[float]] = {}
    for row in history:
        fid = int(row["function_id"])
        if fid not in selected:
            continue
        method = row["method"]
        fe = int(row["evaluations"])
        error = float(row["best_error"])
        if method not in METHODS or not math.isfinite(error) or error < 0:
            raise ValueError("invalid convergence sample")
        by_case.setdefault((fid, method, fe), []).append(error)

    curves: dict[tuple[int, str], list[tuple[int, float]]] = {}
    for fid in selected:
        for method in METHODS:
            checkpoints = sorted(fe for (f, m, fe) in by_case if (f, m) == (fid, method))
            if not checkpoints or checkpoints[0] != 100 or checkpoints[-1] != 10000:
                raise ValueError(f"missing convergence endpoints for F{fid}/{method}")
            if any(len(by_case[(fid, method, fe)]) != 3 for fe in checkpoints):
                raise ValueError(f"unpaired convergence checkpoint for F{fid}/{method}")
            values = [
                (fe, statistics.fmean(by_case[(fid, method, fe)]))
                for fe in checkpoints
            ]
            if values[0][1] <= 0:
                raise ValueError("initial objective error must be positive")
            curves[(fid, method)] = [
                (fe, max(1e-12, value / values[0][1])) for fe, value in values
            ]

    width = 1380
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 560" '
        'role="img" aria-label="Observed CEC2017 convergence at 10k evaluations">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<rect x="16" y="16" width="1348" height="528" rx="18" '
        'fill="#ffffff" stroke="#dde4ee"/>',
        '<text x="55" y="62" font-family="Arial,sans-serif" font-size="26" '
        'font-weight="700" fill="#0f172a">CEC2017 | 10k-FE convergence history</text>',
        '<text x="55" y="92" font-family="Arial,sans-serif" font-size="15" '
        'fill="#64748b">D=30 · 3 matched seeds/method · mean error relative to '
        'the same method at initialization · lower is better</text>',
    ]
    for idx, method in enumerate(METHODS):
        x = 915 + idx * 137
        parts.extend(
            [
                f'<circle cx="{x}" cy="90" r="6" fill="{COLORS[method]}"/>',
                f'<text x="{x+14}" y="96" font-family="Arial,sans-serif" '
                f'font-size="14" fill="#334155">{method.upper()}</text>',
            ]
        )
    for i, fid in enumerate(selected):
        origin_x = 62 + i * 328
        x1 = origin_x + 46
        top, h, w = 154, 307, 236
        minimum = min(value for m in METHODS for _, value in curves[(fid, m)])
        low = min(-1, max(-10, math.floor(math.log10(minimum))))

        def ordinate(value: float, lo: int = low, upper: int = top, height: int = h) -> float:
            return upper + (-math.log10(max(value, 1e-12))) / -lo * height

        parts.extend(
            [
                f'<text x="{x1 + 118}" y="135" text-anchor="middle" '
                f'font-family="Arial,sans-serif" font-weight="700" font-size="21" '
                f'fill="#0f172a">F{fid}</text>',
                f'<line x1="{x1}" y1="{top}" x2="{x1+w}" y2="{top}" stroke="#cbd5e1"/>',
                f'<line x1="{x1}" y1="{top+h}" x2="{x1+w}" y2="{top+h}" '
                'stroke="#cbd5e1"/>',
            ]
        )
        for exponent in range(low, 1):
            y = ordinate(10.0 ** exponent)
            parts.append(
                f'<line x1="{x1}" y1="{y:.2f}" x2="{x1+w}" y2="{y:.2f}" '
                'stroke="#e2e8f0"/>'
            )
        for method in METHODS:
            coords = []
            for fe, ratio in curves[(fid, method)]:
                xp = x1 + (fe - 100) / (10000 - 100) * w
                coords.append(f"{xp:.2f},{ordinate(ratio):.2f}")
            parts.append(
                f'<polyline points="{" ".join(coords)}" fill="none" '
                f'stroke="{COLORS[method]}" stroke-width="3" '
                'stroke-linejoin="round" stroke-linecap="round"/>'
            )
        parts.extend(
            [
                f'<text x="{x1}" y="483" font-family="Arial,sans-serif" '
                'font-size="13" fill="#64748b">100 FE</text>',
                f'<text x="{x1+w}" y="483" text-anchor="end" '
                'font-family="Arial,sans-serif" font-size="13" '
                'fill="#64748b">10,000 FE</text>',
                f'<text x="{x1}" y="507" font-family="Arial,sans-serif" '
                f'font-size="13" fill="#64748b">1x initial</text>',
                f'<text x="{x1+w}" y="507" text-anchor="end" '
                f'font-family="Arial,sans-serif" font-size="13" '
                f'fill="#64748b">min 10^{low}x</text>',
            ]
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"




def leader_transition_counts(
    screen_env: dict, screen_summary: list[dict],
    full_env: dict, full_summary: list[dict],
) -> tuple[dict[tuple[str, str], int], int]:
    """Count observed mean-error leader changes between matched budget cohorts."""

    for field in ("functions", "dimension", "repeats", "base_seed", "reference_commit"):
        if screen_env[field] != full_env[field]:
            raise ValueError(f"leader changes require identical {field}")
    if int(screen_env["evaluations"]) != 1200 or int(full_env["evaluations"]) != 10000:
        raise ValueError("leader transition expects 1200 versus 10000 evaluations")
    former, _ = screen_winners(screen_env, screen_summary)
    later, _ = screen_winners(full_env, full_summary)
    if [fid for fid, _ in former] != [fid for fid, _ in later]:
        raise ValueError("leader comparison has inconsistent function ordering")
    transitions = {(a, b): 0 for a in (*METHODS, "tie") for b in (*METHODS, "tie")}
    changed = 0
    for (_, old_method), (_, new_method) in zip(former, later):
        transitions[(old_method, new_method)] += 1
        changed += old_method != new_method
    if sum(transitions.values()) != 29:
        raise ValueError("leader change study requires all 29 functions")
    return transitions, changed


def leader_transition_svg(
    screen_env: dict, screen_summary: list[dict],
    full_env: dict, full_summary: list[dict],
) -> str:
    """Plot an observed 29-function transition matrix, not simulated outcomes."""

    counts, changed = leader_transition_counts(
        screen_env, screen_summary, full_env, full_summary
    )
    names = (*METHODS, "tie")
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 540" '
        'role="img" aria-label="Observed algorithm leadership changes with budget">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<rect x="18" y="18" width="964" height="505" rx="18" '
        'fill="#ffffff" stroke="#dde4ee"/>',
        '<text x="70" y="73" font-family="Arial,sans-serif" font-size="26" '
        'font-weight="700" fill="#0f172a">CEC2017 | Budget-driven rank changes</text>',
        '<text x="70" y="107" font-family="Arial,sans-serif" font-size="15" '
        'fill="#64748b">29 official functions · D=30 · 3 matched seeds/method · '
        'lowest observed mean error</text>',
        '<text x="517" y="156" font-family="Arial,sans-serif" font-size="17" '
        'font-weight="600" fill="#334155" text-anchor="middle">'
        'Winner at 10,000 function evaluations →</text>',
    ]
    start_x, start_y = 215, 213
    cell_w, cell_h = 158, 64
    for j, method in enumerate(names):
        parts.append(
            f'<text x="{start_x + j * cell_w + cell_w / 2}" y="193" '
            'text-anchor="middle" font-family="Arial,sans-serif" '
            f'font-size="16" fill="#334155">{method.upper()}</text>'
        )
    parts.append(
        '<text x="83" y="196" font-family="Arial,sans-serif" font-size="15" '
        'fill="#64748b">1,200 FE ↓</text>'
    )
    for i, previous in enumerate(names):
        y = start_y + i * cell_h
        parts.append(
            f'<text x="179" y="{y + 38}" text-anchor="end" '
            f'font-family="Arial,sans-serif" font-size="16" '
            f'fill="#334155">{previous.upper()}</text>'
        )
        for j, newer in enumerate(names):
            number = counts[(previous, newer)]
            x = start_x + j * cell_w
            opacity = 0.08 + 0.80 * number / 29
            color = COLORS.get(newer, "#64748b")
            parts.extend(
                [
                    f'<rect x="{x}" y="{y}" width="{cell_w - 9}" '
                    f'height="{cell_h - 8}" rx="7" fill="{color}" '
                    f'fill-opacity="{opacity:.3f}" stroke="#e2e8f0"/>',
                    f'<text x="{x + (cell_w - 9)/2}" y="{y + 34}" '
                    'text-anchor="middle" font-family="Arial,sans-serif" '
                    f'font-size="21" font-weight="700" fill="#0f172a">{number}</text>',
                ]
            )
    parts.extend(
        [
            f'<text x="215" y="504" font-family="Arial,sans-serif" '
            f'font-size="17" font-weight="600" fill="#334155">'
            f'{changed} of 29 functions changed their observed leader</text>',
            '</svg>',
        ]
    )
    return "\n".join(parts) + "\n"


def fullsuite_markdown(
    folder: Path, env: dict, summary: list[dict], tests: list[dict], lang: str,
    previous_environment: dict | None = None,
    previous_summary: list[dict] | None = None,
) -> str:
    _winners, counts = screen_winners(env, summary)
    relative = folder.relative_to(ROOT).as_posix()
    en = lang == "en"
    title = (
        "### All 29 functions at 10,000 evaluations (3 paired seeds)"
        if en else "### 全部 29 个函数：10,000 次评价与收敛曲线"
    )
    lines = [
        title,
        "",
        (
            "**261 real independent optimization trials**; CEC2017 D=30; "
            "ABC, EDBF and RE start each paired repetition from the same seed. "
            "Results remain exploratory because there are just three seeds per function."
            if en else
            "**261 次真实优化试验**，CEC2017 30 维，每方法 3 个配对种子。"
            "每函数重复次数仍较少，结果仅用于探索性比较。"
        ),
        "",
        "![Measured 29-function leaderboard at 10k FEs]"
        "(docs/figures/cec2017-30d-fullsuite-10k-winners.svg)",
        "",
        "![F10 F20 F22 F30 measured convergence histories]"
        "(docs/figures/cec2017-30d-fullsuite-10k-convergence.svg)",
        "",
        (
            "Functions with lowest observed mean error: "
            if en else "观测平均目标误差最低的函数数目："
        ) + ", ".join(f"{m.upper()} {counts[m]}" for m in METHODS)
        + (f", ties {counts['tie']}" if counts["tie"] else "") + ".",
        "",
        (
            "**Across-function paired Wilcoxon tests** on log10 of function-level "
            "mean errors, Holm correction across two contrasts:"
            if en else
            "**跨函数配对 Wilcoxon 检验**（对各函数平均误差取 log10，"
            "两项比较统一 Holm 校正）："
        ),
        "",
        "| Contrast | ABC leads / trails | Raw p | Holm p |"
        if en else "| 对照 | ABC 领先/落后 | 原始 p | Holm 校正 p |",
        "|:---|---:|---:|---:|",
    ]
    for row in tests:
        lines.append(
            f"| {row['comparison']} | {row['wins']}/{row['losses']} | "
            f"{float(row['raw_p']):.5g} | {float(row['holm_p']):.5g} |"
        )
    per_function = {
        (int(row["function_id"]), row["method"]): float(row["mean_error"])
        for row in summary
    }
    lines.extend(
        [
            "",
            (
                "<details><summary>See measured means for all 29 functions</summary>"
                if en else
                "<details><summary>展开查看全部 29 个函数的真实平均误差</summary>"
            ),
            "",
            "| Function | ABC | EDBF | RE |"
            if en else "| 函数 | ABC | EDBF | RE |",
            "|:---|---:|---:|---:|",
        ]
    )
    for fid in env["functions"]:
        values = {method: per_function[(fid, method)] for method in METHODS}
        best = min(values.values())
        rendered = [
            f"**{fmt_error(values[method])}**"
            if math.isclose(values[method], best, rel_tol=1e-12)
            else fmt_error(values[method])
            for method in METHODS
        ]
        lines.append(f"| F{fid} | {' | '.join(rendered)} |")
    lines.extend(["", "</details>", ""])
    lines += [
        "",
        (
            f"[Raw trial CSV]({relative}/trials.csv) · "
            f"[convergence checkpoints]({relative}/history.csv) · "
            f"[per-function metrics]({relative}/summary.csv) · "
            f"[research report]({relative}/report.md) · "
            f"[runtime environment]({relative}/environment.json)"
            if en else
            f"[261 条原始试验]({relative}/trials.csv) · "
            f"[收敛历史]({relative}/history.csv) · "
            f"[逐函数汇总]({relative}/summary.csv) · "
            f"[统计报告]({relative}/report.md) · "
            f"[环境与源码修订]({relative}/environment.json)"
        ),
        "",
        (
            "**Scope:** This is a 10k-FE full-function exploratory benchmark, "
            "not a reproduction of the 100k-FE paper. Different evaluation "
            "budgets and different benchmark backends must never be pooled."
            if en else
            "**适用范围：**这是全部 29 函数的 10k 次评价探索实验，"
            "不是原论文 100k 次评价的完整复现。不同预算、不同基准实现"
            "的数据不得混合统计。"
        ),
    ]
    if previous_environment is not None and previous_summary is not None:
        _, changed = leader_transition_counts(
            previous_environment, previous_summary, env, summary
        )
        lines.extend(
            [
                "",
                "![Observed changes in function-level leading methods]"
                "(docs/figures/cec2017-30d-leader-transitions.svg)",
                "",
                (
                    f"Across 29 functions, {changed} changed their observed "
                    "mean-error leader between 1,200 and 10,000 evaluations."
                    if en else
                    f"在 29 个函数中，有 {changed} 个函数在 1,200 与 10,000 "
                    "次评价之间更换了观测均值领先的方法。"
                ),
                "",
            ]
        )
    return "\n".join(lines)




def load_fresh_seed_holdout() -> tuple[Path, dict, list[dict], list[dict]] | None:
    """Read validated F16/F22 holdout data, never an incomplete trial cohort."""

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    dirname = config.get("holdout_experiment")
    if not dirname:
        return None
    folder = ROOT / dirname
    if not (folder / "summary.csv").is_file():
        return None
    env = json.loads((folder / "environment.json").read_text(encoding="utf-8"))
    if (
        env["functions"] != [16, 22] or env["dimension"] != 30
        or env["repeats"] != 20 or env["evaluations"] != 10000
        or env["seed_base"] != 20261037 or env["trials"] != 120
        or env["reference_commit"] != "424a9fa2757914c3e4cfdd8f59a268b1aeb3197f"
    ):
        raise ValueError("invalid independent holdout protocol")
    with (folder / "summary.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with (folder / "paired_tests.csv").open(newline="", encoding="utf-8") as handle:
        tests = list(csv.DictReader(handle))
    if len(rows) != 6 or len(tests) != 4:
        raise ValueError("missing holdout summaries or statistical tests")
    seen = set()
    for row in rows:
        key = (int(row["function_id"]), row["method"])
        if key in seen or key[0] not in (16, 22) or key[1] not in METHODS:
            raise ValueError("duplicate or unexpected holdout result")
        seen.add(key)
        if int(row["repeats"]) != 20 or int(float(row["mean_evaluations"])) != 10000:
            raise ValueError("incorrect number of paired holdout trials")
        for metric in (
            "mean_error", "std_error", "bootstrap_mean_error_ci95_low",
            "bootstrap_mean_error_ci95_high",
        ):
            if not math.isfinite(float(row[metric])) or float(row[metric]) < 0:
                raise ValueError(f"invalid holdout value {metric}")
        if not (
            float(row["bootstrap_mean_error_ci95_low"])
            <= float(row["bootstrap_mean_error_ci95_high"])
        ):
            raise ValueError("invalid bootstrap interval")
    if seen != {(fid, method) for fid in (16, 22) for method in METHODS}:
        raise ValueError("incomplete holdout method coverage")
    return folder, env, rows, tests


def fresh_seed_holdout_svg(env: dict, summary: list[dict]) -> str:
    """Draw source-backed empirical mean errors and 95% bootstrap whiskers."""

    lookup = {(int(row["function_id"]), row["method"]): row for row in summary}
    all_vals = [
        float(row[field])
        for row in summary
        for field in ("bootstrap_mean_error_ci95_low", "bootstrap_mean_error_ci95_high")
    ]
    if min(all_vals) <= 0:
        raise ValueError("log-scaled holdout plot requires positive measured errors")
    minimum = 10 ** math.floor(math.log10(min(all_vals)))
    maximum = 10 ** math.ceil(math.log10(max(all_vals)))
    lo, hi = math.log10(minimum), math.log10(maximum)
    if hi <= lo:
        raise ValueError("degenerate holdout plot range")
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 580" '
        'role="img" aria-label="F16 F22 independent 20 fresh-seed bootstrap means">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<rect x="20" y="20" width="1060" height="540" rx="16" '
        'fill="#ffffff" stroke="#dde4ee"/>',
        '<text x="65" y="79" font-family="Arial,sans-serif" font-size="28" '
        'font-weight="700" fill="#0f172a">CEC2017 | New-seed robustness check</text>',
        '<text x="65" y="112" font-family="Arial,sans-serif" font-size="16" '
        'fill="#64748b">F16 and F22 · 20 unused paired seeds per method · '
        '10,000 FEs · 95% bootstrap intervals</text>',
        '<text x="65" y="145" font-family="Arial,sans-serif" font-size="14" '
        'fill="#64748b">Lower mean objective error is better '
        '· logarithmic y-axis · bars denote percentile bootstrap CI</text>',
    ]
    top, height = 195, 270

    def ordinate(value: float) -> float:
        return top + height * (hi - math.log10(value)) / (hi - lo)

    for exponent in range(math.ceil(lo), math.floor(hi) + 1):
        tick = 10.0 ** exponent
        y = ordinate(tick)
        parts.extend(
            [
                f'<line x1="145" y1="{y:.2f}" x2="1020" y2="{y:.2f}" '
                'stroke="#e2e8f0"/>',
                f'<text x="130" y="{y+6:.2f}" text-anchor="end" '
                'font-family="Arial,sans-serif" font-size="14" '
                f'fill="#64748b">{tick:.0f}</text>',
            ]
        )
    for fid, center in ((16, 350), (22, 785)):
        parts.append(
            f'<text x="{center}" y="180" text-anchor="middle" '
            'font-family="Arial,sans-serif" font-size="21" '
            f'font-weight="700" fill="#334155">F{fid}</text>'
        )
        for idx, method in enumerate(METHODS):
            row = lookup[(fid, method)]
            mean = float(row["mean_error"])
            lower = float(row["bootstrap_mean_error_ci95_low"])
            upper = float(row["bootstrap_mean_error_ci95_high"])
            x = center + (idx - 1) * 114
            ymean, ylower, yupper = ordinate(mean), ordinate(lower), ordinate(upper)
            color = COLORS[method]
            parts.extend(
                [
                    f'<line x1="{x}" y1="{yupper:.2f}" x2="{x}" '
                    f'y2="{ylower:.2f}" stroke="{color}" stroke-width="5"/>',
                    f'<line x1="{x-13}" y1="{yupper:.2f}" x2="{x+13}" '
                    f'y2="{yupper:.2f}" stroke="{color}" stroke-width="3"/>',
                    f'<line x1="{x-13}" y1="{ylower:.2f}" x2="{x+13}" '
                    f'y2="{ylower:.2f}" stroke="{color}" stroke-width="3"/>',
                    f'<circle cx="{x}" cy="{ymean:.2f}" r="10" '
                    f'fill="{color}" stroke="white" stroke-width="2"/>',
                    f'<text x="{x}" y="492" text-anchor="middle" '
                    'font-family="Arial,sans-serif" font-size="16" '
                    f'fill="#334155">{method.upper()}</text>',
                    f'<title>F{fid} {method.upper()} mean {mean:.8g}, '
                    f'95% bootstrap CI [{lower:.8g}, {upper:.8g}]</title>',
                ]
            )
    parts.append(
        '<text x="65" y="540" font-family="Arial,sans-serif" font-size="14" '
        'fill="#64748b">Intervals reflect resampling 20 new paired seed indices '
        'and should not be interpreted as exact 95% coverage.</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def fresh_seed_holdout_markdown(
    folder: Path, env: dict, summary: list[dict], tests: list[dict], language: str
) -> str:
    en = language == "en"
    relative = folder.relative_to(ROOT).as_posix()
    lookup = {(int(row["function_id"]), row["method"]): row for row in summary}
    lines = [
        (
            "### F16/F22: 20 new seeds to test the unstable rankings"
            if en else
            "### F16、F22：新增 20 个独立种子验证算法排名"
        ),
        "",
        (
            "**120 new measured trials** on F16/F22, D=30, 10,000 function "
            "evaluations, with 20 seed values not reused in previous studies. "
            "ABC/EDBF/RE have matched initial seeds for each repeat."
            if en else
            "**120 次全新实测试验**：F16、F22，30 维，每次 10,000 次函数评价，"
            "每种算法 20 个此前实验没有使用过的配对种子。"
        ),
        "",
        "![F16/F22 holdout mean errors with bootstrap confidence intervals]"
        "(docs/figures/cec2017-f16-f22-holdout-mean-errors.svg)",
        "",
        (
            "**Mean objective error and 95% percentile bootstrap interval** "
            "(lower is better):"
            if en else "**平均目标误差及 95% 百分位 Bootstrap 区间（越低越好）：**"
        ),
        "",
        "| Function | Method | Mean error | 95% bootstrap interval |"
        if en else "| 函数 | 方法 | 平均误差 | Bootstrap 95% 区间 |",
        "|:---|:---|---:|:---|",
    ]
    for fid in (16, 22):
        for method in METHODS:
            row = lookup[(fid, method)]
            lines.append(
                f"| F{fid} | {method.upper()} | "
                f"{fmt_error(float(row['mean_error']))} | "
                f"[{fmt_error(float(row['bootstrap_mean_error_ci95_low']))}, "
                f"{fmt_error(float(row['bootstrap_mean_error_ci95_high']))}] |"
            )
    lines += [
        "",
        (
            "**Two-sided exact paired sign tests, Holm correction for 4 contrasts:**"
            if en else "**双侧配对精确符号检验（4 项比较统一 Holm 校正）：**"
        ),
        "",
        "| Function | Contrast | ABC W/L/T | Holm p |"
        if en else "| 函数 | 对照 | ABC 胜/负/平 | Holm 校正 p |",
        "|:---|:---|---:|---:|",
    ]
    for row in tests:
        lines.append(
            f"| F{row['function_id']} | {row['comparison']} | "
            f"{row['abc_wins']}/{row['abc_losses']}/{row['ties']} | "
            f"{float(row['p_sign_holm']):.5g} |"
        )
    lines += [
        "",
        (
            f"[120 fresh-seed raw trials]({relative}/trials.csv) · "
            f"[bootstrap results]({relative}/summary.csv) · "
            f"[paired hypothesis tests]({relative}/paired_tests.csv) · "
            f"[experiment protocol]({relative}/environment.json) · "
            f"[complete report]({relative}/report.md)"
            if en else
            f"[120 次原始实测]({relative}/trials.csv) · "
            f"[Bootstrap 统计表]({relative}/summary.csv) · "
            f"[配对检验]({relative}/paired_tests.csv) · "
            f"[随机种子与环境]({relative}/environment.json) · "
            f"[完整实验报告]({relative}/report.md)"
        ),
        "",
        (
            "**Caveat:** The functions were selected after earlier ranking "
            "disagreements. Fresh seeds reduce data reuse but this remains "
            "an exploratory two-function study."
            if en else
            "**解释边界：**F16、F22 是此前发现排名分歧后选定的函数；"
            "新种子避免了重复使用旧数据，但本轮仍属于两函数探索性实验。"
        ),
    ]
    return "\n".join(lines)


def inject_readme(old: str, payload: str) -> str:
    if START not in old and END not in old:
        anchor = "## Overview" if payload.startswith("## Measured") else "## 项目定位"
        if anchor not in old:
            raise ValueError(f"README anchor {anchor!r} not found")
        return old.replace(anchor, START + "\n" + payload + "\n" + END + "\n\n" + anchor, 1)
    if old.count(START) != 1 or old.count(END) != 1:
        raise ValueError("ambiguous README experiment markers")
    start = old.index(START)
    end = old.index(END) + len(END)
    return old[:start] + START + "\n" + payload + "\n" + END + old[end:]


def emit(path: Path, content: str, check: bool) -> bool:
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            print(f"OUT OF DATE: {path.relative_to(ROOT)}")
            return False
        print(f"OK: {path.relative_to(ROOT)}")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"UPDATED: {path.relative_to(ROOT)}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="fail if figures or README evidence are stale"
    )
    args = parser.parse_args()
    primary, env, summary, secondary = parse_data()
    outputs = {
        FIGURES / "cec2017-30d-relative-error.svg": evidence_ratio_svg(summary, env),
        FIGURES / "cec2017-30d-runtime.svg": runtime_svg(summary, env),
    }
    screening = load_screening()
    long_budget = load_long_budget()
    full_suite = load_full_suite()
    fresh_holdout = load_fresh_seed_holdout()
    if fresh_holdout is not None:
        _, holdout_env, holdout_summary, _ = fresh_holdout
        outputs[FIGURES / "cec2017-f16-f22-holdout-mean-errors.svg"] = (
            fresh_seed_holdout_svg(holdout_env, holdout_summary)
        )
    if full_suite is not None:
        _, full_env, full_summary, full_history, _ = full_suite
        outputs[FIGURES / "cec2017-30d-fullsuite-10k-winners.svg"] = screening_svg(
            full_env, full_summary
        )
        outputs[FIGURES / "cec2017-30d-fullsuite-10k-convergence.svg"] = (
            fullsuite_convergence_svg(full_history, full_env)
        )
        if screening is not None:
            _, old_env, old_summary = screening
            outputs[FIGURES / "cec2017-30d-leader-transitions.svg"] = leader_transition_svg(
                old_env, old_summary, full_env, full_summary
            )
    if long_budget is not None:
        _, longer_env, longer_summary, _ = long_budget
        outputs[FIGURES / "cec2017-30d-longbudget-relative-error.svg"] = (
            evidence_ratio_svg(longer_summary, longer_env)
        )
        outputs[FIGURES / "cec2017-30d-budget-progression.svg"] = budget_progress_svg(
            summary, longer_summary, env, longer_env
        )
        target, _, _, long_trials = long_budget
        outputs[target / "statistical_analysis_CN.md"] = longbudget_analysis_cn(
            target, longer_env, longer_summary, long_trials, env, summary
        )
    if screening is not None:
        folder, screen_env, screen_data = screening
        outputs[FIGURES / "cec2017-30d-29function-screen.svg"] = screening_svg(
            screen_env, screen_data
        )

    for language, name in (("en", "README.md"), ("cn", "README_CN.md")):
        path = ROOT / name
        markdown = section(primary, secondary, env, summary, language)
        sections = []
        if fresh_holdout is not None:
            folder, holdout_env, holdout_summary, holdout_tests = fresh_holdout
            sections.append(
                fresh_seed_holdout_markdown(
                    folder, holdout_env, holdout_summary, holdout_tests, language
                )
            )
        if full_suite is not None:
            folder, full_env, full_summary, _, full_tests = full_suite
            old_env = screening[1] if screening is not None else None
            old_summary = screening[2] if screening is not None else None
            sections.append(
                fullsuite_markdown(
                    folder, full_env, full_summary, full_tests, language,
                    old_env, old_summary,
                )
            )
        if long_budget is not None:
            folder, long_env, long_data, trials = long_budget
            sections.append(
                longbudget_markdown(
                    folder, long_env, long_data, trials, language, env, summary
                )
            )
        if screening is not None:
            folder, screen_env, screen_data = screening
            sections.append(screening_markdown(folder, screen_env, screen_data, language))
        if sections:
            marker = "<details><summary>"
            if marker not in markdown:
                raise ValueError("10D pilot details block missing from results section")
            markdown = markdown.replace(marker, "\n\n".join(sections) + "\n\n" + marker, 1)
        outputs[path] = inject_readme(
            path.read_text(encoding="utf-8"), markdown
        )
    ok = all(emit(path, text, args.check) for path, text in outputs.items())
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
