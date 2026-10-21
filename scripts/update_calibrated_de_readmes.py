"""Bilingual README results derived solely from sealed calibrated-DE evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from xml.etree import ElementTree

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"docs/experiments/cec2017-calibrated-de-jde-30d-10k-2026-10-21"
START="<!-- CALIBRATED_DE_JDE_START -->"
END="<!-- CALIBRATED_DE_JDE_END -->"
METHODS=("abc","de_tuned","jde")
FIGURES=(
    "cec2017-tuned-de-development-ranks.svg",
    "cec2017-tuned-de-holdout-heatmap.svg",
    "cec2017-tuned-de-holdout-ranks.svg",
    "cec2017-tuned-de-holdout-convergence.svg",
)


def rows(filename:str)->list[dict]:
    with (BASE/filename).open(encoding="utf-8",newline="") as stream:
        return list(csv.DictReader(stream))


def validate()->tuple[dict,dict,list[dict]]:
    env=json.loads((BASE/"environment.json").read_text(encoding="utf-8"))
    choice=json.loads((BASE/"calibration_selection.json").read_text(encoding="utf-8"))
    stats=json.loads((BASE/"global_statistics.json").read_text(encoding="utf-8"))
    calibration=rows("calibration_trials.csv")
    evaluation=rows("evaluation_trials.csv")
    history=rows("evaluation_history.csv")
    summary=rows("summary.csv")
    contrasts=rows("function_sign_tests.csv")
    if (env.get("calibration_trials")!=72 or env.get("evaluation_trials")!=750
            or len(calibration)!=72 or len(evaluation)!=750
            or len(history)!=75000 or len(summary)!=75 or len(contrasts)!=2
            or len(env.get("evaluation_functions",[]))!=25
            or env.get("selected")!=choice.get("selected")
            or stats.get("evaluation_trials")!=750
            or stats.get("permutation_samples")!=20000):
        raise ValueError("incomplete originally executed DE calibration and evaluation evidence")
    expected={(fid,rep,method) for fid in env["evaluation_functions"]
              for rep in range(10) for method in METHODS}
    indexed={(int(row["function_id"]),int(row["repeat"]),row["method"]):row
             for row in evaluation}
    if set(indexed)!=expected or len(indexed)!=750:
        raise ValueError("missing unique, fresh-seed optimizer record")
    for score in summary:
        fid=int(score["function_id"])
        method=score["method"]
        actual=statistics.fmean(float(indexed[(fid,i,method)]["error"])
                                for i in range(10))
        if not math.isclose(
            float(score["mean_error"]),actual,rel_tol=1e-10
        ):
            raise ValueError("a published mean is inconsistent with trial originals")
    for figure in FIGURES:
        path=ROOT/"docs/figures"/figure
        if path.stat().st_size<600 or not ElementTree.parse(path).getroot().tag.endswith("svg"):
            raise ValueError(f"invalid source-derived plot {figure}")
    return choice,stats,contrasts


def block(zh:bool,choice:dict,stats:dict,contrasts:list[dict])->str:
    names={"abc":"ABC","de_tuned":"校准 DE" if zh else "Calibrated DE",
           "jde":"jDE"}
    report_path="docs/experiments/cec2017-calibrated-de-jde-30d-10k-2026-10-21/report.md"
    lines=[
        ("## 新研究：DE 参数校准与自适应 jDE 独立种子验证"
         if zh else "## New study: development-calibrated DE vs self-adaptive jDE"),
        "",
        ("**822 次新优化实验**：先在 F3/F10/F20/F30 上运行72次真实试验，"
         "用固定的六种候选配置选择一个 DE 参数组合；再在其余25个CEC2017函数"
         "上用10个全新配对种子比较 ABC、校准 DE 和自适应 jDE，共750次新试验。"
         "开发阶段和评价阶段分开，且保留82,200条真实收敛记录。"
         if zh else "**822 new optimizer trials**: 72 original experiments on "
         "F3/F10/F20/F30 rank six fixed DE candidates, selecting ONE "
         "configuration without evaluation-function data; 750 fresh-seed "
         "runs then compare ABC, the calibrated DE and standard self-adaptive "
         "jDE across the remaining 25 CEC functions with 10 paired seeds each. "
         "A total of 82,200 authentic convergence checkpoints is archived."),
        "",
        (f"仅依据开发函数选定的 DE 配置：**{choice['selected']}** "
         f"（{choice['strategy']}，F={choice['mutation']}，CR={choice['crossover']}）。"
         if zh else
         f"Development-only selected DE configuration: **{choice['selected']}** "
         f"({choice['strategy']}, F={choice['mutation']}, CR={choice['crossover']})."),
        "",
        "![Calibrated DE candidate ranks on development functions]"
        "(docs/figures/cec2017-tuned-de-development-ranks.svg)",
        "",
        "![All 25 heldout-function measured relative errors]"
        "(docs/figures/cec2017-tuned-de-holdout-heatmap.svg)",
        "",
        "![Full evaluation function-block ranks and method winners]"
        "(docs/figures/cec2017-tuned-de-holdout-ranks.svg)",
        "",
        ("| 方法 | 25函数平均排名（越低越好） | 平均误差最优函数数 | CI机器平均秒数/次 |"
         if zh else "| Algorithm | Mean rank (lower better) | Best-mean functions | Hosted seconds/run |"),
        "|:---|---:|---:|---:|",
    ]
    for method in METHODS:
        lines.append(
            f"| {names[method]} | {stats['mean_function_ranks'][method]:.3f} | "
            f"{stats['function_winner_counts'][method]}/25 | "
            f"{stats['mean_wall_seconds_per_run'][method]:.3f} |"
        )
    lines.extend([
        "",
        (f"仅本轮25函数的随机标签 Friedman 检验："
         f"Q={stats['friedman_statistic']:.4f}，p={stats['permutation_p']:.5g}"
         "（20,000次置换）。"
         if zh else
         f"Within-evaluation function-block randomized-label Friedman: "
         f"Q={stats['friedman_statistic']:.4f}, "
         f"p={stats['permutation_p']:.5g} (20,000 permutations)."),
        "",
        ("| 预设比较 | ABC胜/负/平（按函数） | Holm p |"
         if zh else "| Prespecified contrast | ABC function wins/losses/ties | Holm p |"),
        "|:---|---:|---:|",
    ])
    for contrast in contrasts:
        other=contrast["comparison"].removeprefix("abc_vs_")
        lines.append(
            f"| ABC vs {names[other]} | "
            f"{contrast['abc_function_wins']}/{contrast['abc_function_losses']}/"
            f"{contrast['ties']} | {float(contrast['holm_sign_p']):.5g} |"
        )
    lines.extend([
        "",
        "![Actual median and IQR convergence on four prespecified evaluation functions]"
        "(docs/figures/cec2017-tuned-de-holdout-convergence.svg)",
        "",
        ("**重要边界：**这里的25函数仅未参与本轮DE参数选择，"
         "它们已在早期 BoundEvo 实验中被观察过，不能称为从未见过的测试函数。"
         "仅比较一组校准 DE 和经典 jDE，不等于证明胜过 SHADE、L-SHADE"
         "等更先进的竞争基线。函数评价公平不等于计算耗时公平。"
         if zh else "**Limits:** All 25 evaluation functions are new only "
         "to this round's DE calibration; they appeared in earlier BoundEvo "
         "experiments. No never-seen-function claim is made. jDE and the "
         "limited six-candidate DE calibration do not represent all advanced "
         "SHADE/L-SHADE-class methods. FE parity is not CPU-time parity."),
        "",
        (f"[全部原始试验及报告]({report_path}) · "
         "[预先冻结的开发-评价分割协议](docs/calibrated_de_jde_protocol.md)"
         if zh else
         f"[Original calibration/evaluation data and full report]({report_path}) · "
         "[Frozen calibration/evaluation protocol](docs/calibrated_de_jde_protocol.md)"),
        "",
    ])
    return "\n".join(lines)


def patch(source:str,text:str)->str:
    payload=START+"\n"+text+"\n"+END
    if START in source or END in source:
        if source.count(START)!=1 or source.count(END)!=1:
            raise ValueError("ambiguous existing calibrated-DE section")
        return source[:source.index(START)]+payload+source[source.index(END)+len(END):]
    anchor="<!-- FULLSUITE_DE_RESULTS_END -->"
    if source.count(anchor)!=1:
        raise ValueError("previous full-suite scientific evidence anchor missing")
    return source.replace(anchor,anchor+"\n\n"+payload,1)


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    choice,stats,tests=validate()
    for is_zh,path in ((False,ROOT/"README.md"),(True,ROOT/"README_CN.md")):
        output=patch(path.read_text(encoding="utf-8"),block(is_zh,choice,stats,tests))
        if args.check:
            if path.read_text(encoding="utf-8")!=output:
                raise SystemExit("outdated empirical README "+str(path))
        else:
            path.write_text(output,encoding="utf-8")
            print(f"UPDATED bilingual scientific evidence: {path.name}")


if __name__=="__main__":
    main()
