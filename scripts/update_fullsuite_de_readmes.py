"""Inject verified full-function DE comparison data into bilingual research summaries."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT/"docs/experiments/cec2017-fullsuite-de-30d-10k-2026-10-21"
BEGIN = "<!-- FULLSUITE_DE_RESULTS_START -->"
END = "<!-- FULLSUITE_DE_RESULTS_END -->"
METHODS = ("abc", "abc_reverse", "de_rand1bin")
FIGURES = (
    "cec2017-fullsuite-de-relative-heatmap.svg",
    "cec2017-fullsuite-de-ranks.svg",
    "cec2017-fullsuite-de-four-convergence.svg",
)


def read(filename: str) -> list[dict]:
    with (DIR/filename).open(newline="",encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate() -> tuple[dict,list[dict],list[dict]]:
    env = json.loads((DIR/"environment.json").read_text(encoding="utf-8"))
    stats = json.loads((DIR/"global_statistics.json").read_text(encoding="utf-8"))
    trials, summary, tests = read("trials.csv"), read("summary.csv"), read("function_sign_tests.csv")
    history, ranks = read("history.csv"), read("function_ranks.csv")
    fids = (1,*range(3,31))
    if (env.get("functions") != list(fids) or env.get("methods") != list(METHODS)
            or env.get("trials") != 435 or env.get("history_rows") != 43500
            or len(trials) != 435 or len(history) != 43500
            or len(summary) != 87 or len(ranks) != 87 or len(tests) != 3):
        raise ValueError("incomplete full-suite original evidence")
    expected = {(fid,r,m) for fid in fids for r in range(5) for m in METHODS}
    keys = {(int(t["function_id"]),int(t["repeat"]),t["method"]) for t in trials}
    if keys != expected or len(keys) != len(trials):
        raise ValueError("missing or duplicated original optimizer trials")
    for fid in fids:
        for method in METHODS:
            vals = [float(t["error"]) for t in trials
                    if int(t["function_id"]) == fid and t["method"] == method]
            group = [float(s["mean_error"]) for s in summary
                     if int(s["function_id"]) == fid and s["method"] == method]
            if len(vals)!=5 or len(group)!=1 or not math.isclose(
                statistics.fmean(vals),group[0],rel_tol=1e-10
            ):
                raise ValueError("README scientific mean cannot reproduce original evidence")
    for name in FIGURES:
        path=ROOT/"docs/figures"/name
        if path.stat().st_size < 6500 or not ElementTree.parse(path).getroot().tag.endswith("svg"):
            raise ValueError("invalid original-data scientific figure")
    if stats.get("functions")!=29 or stats.get("trials")!=435:
        raise ValueError("incorrect global statistics coverage")
    return stats,summary,tests


def content(zh: bool, stats: dict, tests: list[dict]) -> str:
    names={"abc":"ABC","abc_reverse":"ABC-Reverse","de_rand1bin":"DE/rand/1/bin"}
    lines=[
        ("## 29 函数独立复核：ABC 与标准差分进化"
         if zh else "## Complete 29-function replication with differential evolution"),
        "",
        ("**435 次新运行**，覆盖 CEC2017 所有29个保留函数（F1、F3–F30），"
         "30维，每函数每方法5个全新配对种子，统一10,000次函数评价；"
         "三种算法采用完全相同的初始种群，保留43,500条真实收敛记录。"
         if zh else "**435 NEW real optimizer trials** spanning all 29 retained "
         "CEC2017 tasks (F1, F3–F30), 30D, five fresh paired seeds and "
         "10,000 evaluations per algorithm/function. All three methods "
         "share identical initial populations; 43,500 authentic convergence "
         "checkpoints have been archived."),
        "",
        "![All-function empirical relative-error heatmap](docs/figures/cec2017-fullsuite-de-relative-heatmap.svg)",
        "",
        "![Actual function-block rank and win distribution](docs/figures/cec2017-fullsuite-de-ranks.svg)",
        "",
        ("| 算法 | 29函数平均排名（越低越好） | 最优函数数量 |"
         if zh else "| Method | Mean rank over 29 functions (lower better) | Best-mean functions |"),
        "|:---|---:|---:|",
    ]
    for m in METHODS:
        lines.append(f"| {names[m]} | {stats['function_block_mean_ranks'][m]:.3f} | "
                     f"{stats['function_best_mean_error_counts'][m]}/29 |")
    lines.extend([
        "",
        (f"函数分组 Friedman 秩统计量 Q={stats['friedman_rank_statistic']:.4f}；"
         f"20,000次随机标签置换 p={stats['permutation_p']:.5g}。"
         if zh else
         f"Function-block Friedman Q={stats['friedman_rank_statistic']:.4f}; "
         f"20,000-label-permutation p={stats['permutation_p']:.5g}."),
        "",
        "![Measured median/IQR convergence on four preset functions](docs/figures/cec2017-fullsuite-de-four-convergence.svg)",
        "",
        ("| 跨函数配对 | 方法A胜/方法B胜/平 | Holm校正 p |"
         if zh else "| Across-function pair | A wins/B wins/ties | Holm p |"),
        "|:---|---:|---:|",
    ])
    for test in tests:
        a,b=test["method_a"],test["method_b"]
        lines.append(f"| {names[a]} vs {names[b]} | "
                     f"{test['a_function_wins']}/{test['a_function_losses']}/{test['ties']} | "
                     f"{float(test['holm_function_sign_p']):.5g} |")
    lines.extend([
        "",
        ("**限制：**DE 是未经超参数搜索的标准配置（F=0.8、CR=0.9、NP=100），"
         "仅5种子/函数，不可据此断言每个函数上的小幅优势。CEC2017并非"
         "所有问题的随机样本；等评价次数不等运行时间。"
         "后端为 C 源码衍生 Python 参考实现，不是赛事官方 C 可执行程序。"
         if zh else "**Limits:** DE was not hyperparameter-tuned (fixed "
         "F=0.8, CR=0.9, NP=100). Five seeds/function cannot resolve small "
         "individual-function effects. Curated CEC2017 functions are not "
         "a random population of optimization problems; equal FE is not equal "
         "runtime. The backend is a C-derived Python port, not the official C executable."),
        "",
        ("[全29函数原始统计与实验报告]"
         "(docs/experiments/cec2017-fullsuite-de-30d-10k-2026-10-21/report.md) · "
         "[实验前冻结方案](docs/fullsuite_de_protocol.md)"
         if zh else "[All 29 function results and original scientific evidence]"
         "(docs/experiments/cec2017-fullsuite-de-30d-10k-2026-10-21/report.md) · "
         "[Frozen protocol](docs/fullsuite_de_protocol.md)"),
        "",
    ])
    return "\n".join(lines)


def update(text: str, block: str) -> str:
    artifact=BEGIN+"\n"+block+"\n"+END
    if BEGIN in text or END in text:
        if text.count(BEGIN)!=1 or text.count(END)!=1:
            raise ValueError("ambiguous existing full-suite markers")
        return text[:text.index(BEGIN)]+artifact+text[text.index(END)+len(END):]
    anchor="<!-- REVERSE_MECHANISM_RESULTS_END -->"
    if text.count(anchor)!=1:
        raise ValueError("missing validated earlier research evidence anchor")
    return text.replace(anchor,anchor+"\n\n"+artifact,1)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    stats,summary,tests=validate()
    for language,filename in ((False,"README.md"),(True,"README_CN.md")):
        path=ROOT/filename
        rendered=update(path.read_text(encoding="utf-8"),content(language,stats,tests))
        if args.check:
            if path.read_text(encoding="utf-8") != rendered:
                raise SystemExit(f"outdated original-science README: {filename}")
        else:
            path.write_text(rendered,encoding="utf-8")
            print(f"UPDATED {filename}")
    print("All original 29-function scientific README records reconcile.")


if __name__=="__main__":
    main()
