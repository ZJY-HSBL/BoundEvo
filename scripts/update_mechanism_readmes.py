"""Insert research-validated coefficient-position results into both READMEs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "docs/experiments/cec2017-abc-reverse-30d-10k-2026-10-20"
FIGURES = ROOT / "docs/figures"
FIRST = "<!-- REVERSE_MECHANISM_RESULTS_START -->"
LAST = "<!-- REVERSE_MECHANISM_RESULTS_END -->"
METHODS = ("abc", "abc_shuffle", "abc_reverse")
FIDS = (10, 16, 20, 22)


def load() -> tuple[dict, list[dict], list[dict], dict]:
    env = json.loads((FOLDER/"environment.json").read_text(encoding="utf-8"))
    def tab(name: str) -> list[dict]:
        with (FOLDER/name).open(newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))
    trial, summary, tests, audit, history = (
        tab("trials.csv"), tab("summary.csv"), tab("paired_tests.csv"),
        tab("coefficient_position_audit.csv"), tab("history.csv")
    )
    if (env.get("functions") != list(FIDS) or env.get("methods") != list(METHODS)
            or env.get("trials") != 144 or env.get("history_rows") != 3312
            or env.get("repeats") != 12 or env.get("evaluations") != 10_000
            or env.get("audit_draws") != 50_000
            or len(trial) != 144 or len(history) != 3312
            or len(summary) != 12 or len(tests) != 8 or len(audit) != 15):
        raise ValueError("incomplete measured three-arm evidence")
    expected = {(f, i, method) for f in FIDS for i in range(12) for method in METHODS}
    actual = {(int(t["function_id"]), int(t["repeat"]), t["method"]) for t in trial}
    if actual != expected or len(set(actual)) != len(trial):
        raise ValueError("unmatched / duplicate empirical optimizer data")
    indexed = {(int(row["function_id"]), row["method"]): row for row in summary}
    if set(indexed) != {(f, m) for f in FIDS for m in METHODS}:
        raise ValueError("missing method summaries")
    for key, row in indexed.items():
        vals = [float(t["error"]) for t in trial
                if (int(t["function_id"]), t["method"]) == key]
        if len(vals) != 12 or not math.isclose(
            statistics.fmean(vals), float(row["mean_error"]), rel_tol=1e-10
        ):
            raise ValueError("scientific figure/README mean differs from raw trials")
    contrasts = {(int(t["function_id"]), t["contrast"]) for t in tests}
    if contrasts != {(f, f"{m}_vs_abc") for f in FIDS
                     for m in ("abc_shuffle", "abc_reverse")}:
        raise ValueError("missing eight prespecified Holm contrasts")
    overview = json.loads((FOLDER/"coefficient_audit.json").read_text(encoding="utf-8"))
    if (overview.get("total_draws") != 50_000
            or not 0 <= overview.get("mean_elite_share_absolute_mass", -1) <= 1):
        raise ValueError("unsupported coefficient audit")
    for name in ("cec2017-coefficient-rank-144-paired-effects.svg",
                 "cec2017-abc-50000-coefficient-position.svg"):
        p = FIGURES/name
        if p.stat().st_size < 4500 or not ElementTree.parse(p).getroot().tag.endswith("svg"):
            raise ValueError(f"invalid real scientific figure {name}")
    return env, summary, tests, overview


def text_block(language: str, summary: list[dict], tests: list[dict], audit: dict) -> str:
    chinese = language == "cn"
    title = (
        "## 系数顺序机制验证：ABC / 随机置换 / 确定性反序"
        if chinese else "## Coefficient-order mechanism: ABC / Shuffle / Reverse"
    )
    intro = (
        "**144 次新的真实优化试验**：F10/F16/F20/F22、30维、10k评价预算、"
        "每函数12个全新配对种子。ABC-Reverse 保留全部原始系数，直接反转位置，"
        "**不额外消耗随机数**；可与随机置换版本对比，用于检验精英父代排序耦合假设。"
        if chinese else
        "**144 additional real optimizer runs**: F10/F16/F20/F22, 30D, "
        "10k function evaluations, 12 fresh paired seeds/function. ABC-Reverse "
        "reverses the original valid coefficient vector **without consuming "
        "extra RNG draws**; comparison to the random-shuffle control probes "
        "potential coefficient-index / elite-parent-rank coupling."
    )
    index = {(int(row["function_id"]), row["method"]): row for row in summary}
    testing = {(int(r["function_id"]), r["contrast"]): r for r in tests}
    lines = [
        title, "", intro, "",
        "![Measured three-arm paired-seed effects](docs/figures/cec2017-coefficient-rank-144-paired-effects.svg)",
        "",
        ("| 函数 | ABC 均值误差 | 随机置换均值误差 | 反序均值误差 |"
         if chinese else "| Function | ABC mean error | Shuffle mean error | Reverse mean error |"),
        "|:---|---:|---:|---:|",
    ]
    for fid in FIDS:
        values = [float(index[(fid, method)]["mean_error"]) for method in METHODS]
        winning = min(values)
        formatted = [f"**{v:,.2f}**" if math.isclose(v, winning, rel_tol=1e-12)
                     else f"{v:,.2f}" for v in values]
        lines.append(f"| F{fid} | "+" | ".join(formatted)+" |")
    lines.extend([
        "",
        ("**八项预先规定的配对符号检验（统一 Holm 校正）**："
         if chinese else "**Eight designated paired sign tests (one Holm family):**"),
        "",
        ("| 函数 | 对照方法 | 对照胜/ABC胜/平 | 校正 p |"
         if chinese else "| Function | Control | Control wins / ABC wins / ties | Adjusted p |"),
        "|:---|:---|---:|---:|",
    ])
    for fid in FIDS:
        for method in ("abc_shuffle", "abc_reverse"):
            row = testing[(fid, f"{method}_vs_abc")]
            lines.append(
                f"| F{fid} | {method} | {row['control_wins']}/"
                f"{row['abc_wins']}/{row['ties']} | "
                f"{float(row['holm_sign_p']):.5g} |"
            )
    lines.extend([
        "",
        "![Original ABC coefficient position marginal audit](docs/figures/cec2017-abc-50000-coefficient-position.svg)",
        "",
        (f"另对 **50,000 组真实 ABC 系数向量**进行位置分布审计。"
         f"前5个精英父代槽位所占绝对权重总量的平均比例为"
         f" **{100*audit['mean_elite_share_absolute_mass']:.2f}%**；"
         "该统计反映采样位置效应，不等于算法精度优势的因果证明。"
         if chinese else
         f"Separate Monte Carlo audit of **50,000 actual ABC vectors**: "
         f"the first five elite-parent slots account for an average "
         f"**{100*audit['mean_elite_share_absolute_mass']:.2f}%** of total "
         "absolute coefficient mass. A marginal-position distribution "
         "does not establish a causal optimization benefit."),
        "",
        ("**科研边界**：函数仍是研究后自适应挑选的子集；反序只控制额外 RNG "
         "调用，不能使后续搜索轨迹保持一致。结果是机制探索，不应宣传为"
         "29函数标准实验或已确认的新算法优势。"
         if chinese else
         "**Scope:** functions were selected adaptively; reversal eliminates "
         "extra permutation RNG draws but cannot freeze future diverged trajectories. "
         "This is exploratory mechanistic evidence, not a complete 29-function "
         "benchmark or proven superiority."),
        "",
        ("[完整原始数据与分析](docs/experiments/cec2017-abc-reverse-30d-10k-2026-10-20/report.md) · "
         "[冻结实验方案](docs/abc_reverse_mechanism_protocol.md)"
         if chinese else
         "[All original records and statistical report](docs/experiments/cec2017-abc-reverse-30d-10k-2026-10-20/report.md) · "
         "[Frozen experiment protocol](docs/abc_reverse_mechanism_protocol.md)"),
        "",
    ])
    return "\n".join(lines)


def render(source: str, block: str) -> str:
    full = FIRST+"\n"+block+"\n"+LAST
    if FIRST in source or LAST in source:
        if source.count(FIRST) != 1 or source.count(LAST) != 1:
            raise ValueError("ambiguous README coefficient mechanism markers")
        return source[:source.index(FIRST)] + full + source[
            source.index(LAST)+len(LAST):
        ]
    anchor = "<!-- ADVANCED_RESEARCH_END -->"
    if source.count(anchor) != 1:
        raise ValueError("expected previous measured research section")
    return source.replace(anchor, anchor+"\n\n"+full, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    _env, summary, tests, overview = load()
    for lang, filename in (("en", "README.md"), ("cn", "README_CN.md")):
        path = ROOT/filename
        content = render(path.read_text(encoding="utf-8"), text_block(
            lang, summary, tests, overview
        ))
        if args.check:
            if path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"outdated scientific evidence in {filename}")
            print(f"OK: {filename}")
        else:
            path.write_text(content, encoding="utf-8")
            print(f"UPDATED: {filename}")


if __name__ == "__main__":
    main()
