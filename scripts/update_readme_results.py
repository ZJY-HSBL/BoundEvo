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
    return folder, environment, summary, trials




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
                f"[environment]({loc}/environment.json)"
                if en else
                f"[120 次原始试验]({loc}/trials.csv) · "
                f"[均值和方差]({loc}/summary.csv) · "
                f"[配对检验]({loc}/paired_sign_tests.csv) · "
                f"[环境记录]({loc}/environment.json)"
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
    if long_budget is not None:
        _, longer_env, longer_summary, _ = long_budget
        outputs[FIGURES / "cec2017-30d-longbudget-relative-error.svg"] = (
            evidence_ratio_svg(longer_summary, longer_env)
        )
    if screening is not None:
        folder, screen_env, screen_data = screening
        outputs[FIGURES / "cec2017-30d-29function-screen.svg"] = screening_svg(
            screen_env, screen_data
        )

    for language, name in (("en", "README.md"), ("cn", "README_CN.md")):
        path = ROOT / name
        markdown = section(primary, secondary, env, summary, language)
        if long_budget is not None:
            folder, long_env, long_data, trials = long_budget
            long_section = longbudget_markdown(
                folder, long_env, long_data, trials, language, env, summary
            )
            markdown = markdown.replace(
                "<details><summary>", long_section + "\n\n<details><summary>", 1
            )
        if screening is not None:
            folder, screen_env, screen_data = screening
            extra_section = screening_markdown(folder, screen_env, screen_data, language)
            marker = "<details><summary>"
            if marker not in markdown:
                raise ValueError("10D pilot details block missing from results section")
            markdown = markdown.replace(marker, extra_section + "\n\n" + marker, 1)
        outputs[path] = inject_readme(
            path.read_text(encoding="utf-8"), markdown
        )
    ok = all(emit(path, text, args.check) for path, text in outputs.items())
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
