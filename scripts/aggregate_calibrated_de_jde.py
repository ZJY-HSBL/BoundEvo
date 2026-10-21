"""Evaluate 25-function calibrated DE and jDE outcomes from genuine original records."""

# ruff: noqa: ISC004

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from html import escape
from itertools import pairwise
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
from run_tuned_de_jde import (
    BUDGET,
    DEV_FUNCTIONS,
    EVAL_METHODS,
    TEST_FUNCTIONS,
    TEST_SEED,
    TEST_SHARDS,
)
from select_de_calibration import calibrate

from boundevo.cec2017 import REFERENCE_COMMIT

METHODS=EVAL_METHODS
SAMPLES=10_000
PERMUTATIONS=20_000
COLORS={"abc":"#20678d","de_tuned":"#c47734","jde":"#348b74"}
REPORT_DIR="docs/experiments/cec2017-calibrated-de-jde-30d-10k-2026-10-21"


def csv_read(p:Path)->list[dict]:
    if not p.is_file():
        raise ValueError(f"missing actual new optimizer evidence: {p}")
    with p.open(newline="",encoding="utf-8") as stream:
        rows=list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"empty original experiment evidence: {p}")
    return rows


def csv_write(p:Path,rows:list[dict])->None:
    if not rows:
        raise ValueError("cannot publish empty original research table")
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open(newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def verify(
    dev_dir:Path,holdout_dir:Path,selection_file:Path
)->tuple[list[dict],list[dict],dict,list[dict],list[dict]]:
    chosen,dev_function,dev_board=calibrate(dev_dir)
    supplied=json.loads(selection_file.read_text(encoding="utf-8"))
    if chosen != supplied:
        raise ValueError("calibration selection differs from actual 72 original trials")
    original,history,manifests=[],[],[]
    sha=chosen["calibration_source_commit"]
    evaluation_sha=None
    for shard,fids in enumerate(TEST_SHARDS):
        directory=holdout_dir/f"shard{shard}"
        manifest=json.loads((directory/"manifest.json").read_text(encoding="utf-8"))
        expected={
            "phase":"evaluation","task_id":shard,"functions":list(fids),
            "methods":list(METHODS),"dimension":30,"repeats":10,
            "seed_base":TEST_SEED,"evaluations":BUDGET,
            "population":100,"history_step_fe":100,
            "reference_commit":REFERENCE_COMMIT,
            "calibration_source_commit":sha,
            "selected_de":chosen,
        }
        if any(manifest.get(k)!=v for k,v in expected.items()):
            raise ValueError(f"incorrect frozen holdout settings in shard {shard}")
        if not manifest.get("source_commit") or (
            evaluation_sha is not None and evaluation_sha!=manifest["source_commit"]
        ):
            raise ValueError("holdout jobs must share one exact source commit")
        evaluation_sha=manifest["source_commit"]
        trials=csv_read(directory/"trials.csv")
        curve=csv_read(directory/"history.csv")
        if len(trials)!=len(fids)*30 or len(curve)!=len(fids)*3000:
            raise ValueError(f"missing original holdout optimizer trials shard{shard}")
        original.extend(trials)
        history.extend(curve)
        manifests.append(manifest)
    all_keys={(fid,repeat,m) for fid in TEST_FUNCTIONS
              for repeat in range(10) for m in METHODS}
    by_key={}
    for item in original:
        key=(int(item["function_id"]),int(item["repeat"]),item["method"])
        if key not in all_keys or key in by_key:
            raise ValueError(f"duplicate/unexpected holdout optimizer run {key}")
        fid,repeat,method=key
        if (int(item["seed"])!=TEST_SEED+10000*fid+repeat
                or int(item["dimension"])!=30 or int(item["evaluations"])!=10000
                or float(item["optimum"])!=fid*100.0
                or int(item["coefficient_attempts"])!=(9900 if method=="abc" else 0)):
            raise ValueError(f"invalid holdout FE/seed/coefficient evaluations {key}")
        if any(not math.isfinite(float(item[k])) for k in
               ("objective","optimum","error","elapsed_seconds","violation")):
            raise ValueError(f"nonfinite holdout original trial {key}")
        if float(item["error"])<0 or not math.isclose(
            float(item["objective"])-float(item["optimum"]),
            float(item["error"]),rel_tol=1e-10,abs_tol=1e-6
        ):
            raise ValueError(f"CEC gap mismatch {key}")
        by_key[key]=item
    if len(original)!=750 or set(by_key)!=all_keys:
        raise ValueError("exactly 750 fresh original holdout trials required")
    traces=defaultdict(list)
    for row in history:
        key=(int(row["function_id"]),int(row["repeat"]),row["method"])
        if key not in all_keys or int(row["seed"])!=int(by_key[key]["seed"]):
            raise ValueError("unknown/mislabeled fresh optimizer history")
        traces[key].append(row)
    if len(history)!=75_000 or set(traces)!=all_keys:
        raise ValueError("all 75000 fresh original convergence checkpoints required")
    fes=list(range(100,10_001,100))
    for key,values in traces.items():
        values.sort(key=lambda row:int(row["evaluations"]))
        evals=[int(row["evaluations"]) for row in values]
        err=[float(row["best_error"]) for row in values]
        if (evals!=fes or any(not math.isfinite(v) or v<0 for v in err)
                or any(b>a+1e-7 for a,b in pairwise(err))
                or not math.isclose(err[-1],float(by_key[key]["error"]),
                                    rel_tol=1e-10,abs_tol=1e-6)):
            raise ValueError(f"invalid actual best-so-far trace {key}")
    for fid in TEST_FUNCTIONS:
        for rep in range(10):
            beginnings=[float(traces[(fid,rep,m)][0]["best_error"]) for m in METHODS]
            if max(beginnings)-min(beginnings)>1e-7:
                raise ValueError("ABC, DE, jDE didn't receive paired initial populations")
    original.sort(key=lambda row:(int(row["function_id"]),int(row["repeat"]),row["method"]))
    history.sort(key=lambda row:(
        int(row["function_id"]),int(row["repeat"]),row["method"],
        int(row["evaluations"])
    ))
    return original,history,chosen,dev_function,dev_board


def midrank3(values:list[float])->list[float]:
    if len(values)!=3:
        raise ValueError("three method scores required")
    return [1+sum(v<x for v in values)
            +(sum(v==x for v in values)-1)/2 for x in values]


def friedman(matrix:np.ndarray)->float:
    n,k=matrix.shape
    if k!=3:
        raise ValueError("Friedman needs three algorithms")
    means=matrix.mean(axis=0)
    return float(12*n/(k*(k+1))*np.sum((means-(k+1)/2)**2))


def sign(wins:int,losses:int)->float:
    n=wins+losses
    return min(1.,2*sum(math.comb(n,i)
                       for i in range(min(wins,losses)+1))/2**n)


def analyze(trials:list[dict])->tuple[list[dict],list[dict],list[dict],dict]:
    by_key={(int(r["function_id"]),int(r["repeat"]),r["method"]):r for r in trials}
    if len(by_key)!=750:
        raise ValueError("cannot analyze incomplete 750-run heldout cohort")
    summary,rank_rows=[],[]
    for fid in TEST_FUNCTIONS:
        random=np.random.default_rng(TEST_SEED+fid+73)
        bootstrap=random.integers(0,10,size=(SAMPLES,10))
        means=[]
        for method in METHODS:
            vals=np.asarray([float(by_key[(fid,repeat,method)]["error"])
                             for repeat in range(10)],dtype=float)
            bounds=np.quantile(vals[bootstrap].mean(axis=1),(0.025,0.975))
            mean=float(vals.mean())
            means.append(mean)
            runtime=[float(by_key[(fid,repeat,method)]["elapsed_seconds"])
                     for repeat in range(10)]
            summary.append({
                "function_id":fid,"method":method,"seeds":10,"mean_error":mean,
                "median_error":float(np.median(vals)),
                "std_error":float(np.std(vals,ddof=1)),
                "bootstrap_mean_ci95_low":float(bounds[0]),
                "bootstrap_mean_ci95_high":float(bounds[1]),
                "mean_elapsed_seconds":statistics.fmean(runtime),
            })
        for method,value,rnk in zip(METHODS,means,midrank3(means)):
            rank_rows.append({
                "function_id":fid,"method":method,"mean_error":value,
                "rank":rnk,
                "relative_to_function_best":(1+value)/(1+min(means)),
            })
    ranks=np.asarray([
        [next(float(row["rank"]) for row in rank_rows
              if int(row["function_id"])==fid and row["method"]==method)
         for method in METHODS]
        for fid in TEST_FUNCTIONS
    ],dtype=float)
    q=friedman(ranks)
    rng=np.random.default_rng(20262219)
    count=0
    for _ in range(PERMUTATIONS):
        block=np.stack([row[rng.permutation(3)] for row in ranks])
        if friedman(block)>=q-1e-12:
            count+=1
    contrasts=[]
    for contender in ("de_tuned","jde"):
        a=sum(
            next(float(t["mean_error"]) for t in rank_rows
                 if int(t["function_id"])==fid and t["method"]=="abc")
            <
            next(float(t["mean_error"]) for t in rank_rows
                 if int(t["function_id"])==fid and t["method"]==contender)
            for fid in TEST_FUNCTIONS
        )
        b=sum(
            next(float(t["mean_error"]) for t in rank_rows
                 if int(t["function_id"])==fid and t["method"]=="abc")
            >
            next(float(t["mean_error"]) for t in rank_rows
                 if int(t["function_id"])==fid and t["method"]==contender)
            for fid in TEST_FUNCTIONS
        )
        contrasts.append({
            "comparison":f"abc_vs_{contender}",
            "abc_function_wins":a,"abc_function_losses":b,
            "ties":25-a-b,"exact_sign_p":sign(a,b),"holm_sign_p":1.,
        })
    correction=0.
    for idx,position in enumerate(sorted(
        range(2),key=lambda j:contrasts[j]["exact_sign_p"]
    )):
        correction=max(
            correction,min(1.,contrasts[position]["exact_sign_p"]*(2-idx))
        )
        contrasts[position]["holm_sign_p"]=correction
    stats={
        "development_functions":list(DEV_FUNCTIONS),
        "evaluation_functions":list(TEST_FUNCTIONS),
        "evaluation_function_count":25,
        "evaluation_trials":750,
        "evaluation_checkpoints":75000,
        "mean_function_ranks":{
            m:float(ranks[:,idx].mean()) for idx,m in enumerate(METHODS)
        },
        "function_winner_counts":{
            m:int(sum(row[idx]==min(row) for row in ranks))
            for idx,m in enumerate(METHODS)
        },
        "mean_wall_seconds_per_run":{
            m:statistics.fmean(float(r["mean_elapsed_seconds"])
                               for r in summary if r["method"]==m)
            for m in METHODS
        },
        "friedman_statistic":q,
        "permutation_samples":PERMUTATIONS,
        "permutation_p":(count+1)/(PERMUTATIONS+1),
        "permutation_extremes":count,
        "bootstrap_samples":SAMPLES,
        "interpretation":"exploratory function-block inference on previously studied CEC2017 functions",
    }
    return summary,rank_rows,contrasts,stats


def svg_header(w:int,h:int,title:str,subtitle:str)->list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">',
        f'<rect width="{w}" height="{h}" fill="#f7f9fc"/>',
        f'<text x="56" y="55" font-family="Arial" font-size="26" '
        f'font-weight="700" fill="#1a2c42">{escape(title)}</text>',
        f'<text x="56" y="84" font-family="Arial" font-size="14" '
        f'fill="#64748b">{escape(subtitle)}</text>',
    ]


def tx(x:float,y:float,t:str,size:int=13,color:str="#334155",
       anchor:str="start",weight:int=400)->str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial" '
            f'font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{weight}">{escape(t)}</text>')


def calibration_svg(rows:list[dict],choice:dict)->str:
    board={r["candidate_id"]:float(r["average_development_function_rank"])
           for r in rows}
    sequence=list(board)
    out=svg_header(1170,640,"Development-only DE calibration",
                   "F3/F10/F20/F30 · 3 seeds × 6 fixed candidates · 72 original trials · lower rank is better")
    out.append('<rect x="58" y="118" width="1053" height="456" rx="13" '
               'fill="white" stroke="#e3e8f0"/>')
    for i,candidate in enumerate(sequence):
        y=183+i*62
        val=board[candidate]
        chosen=candidate==choice["selected"]
        color="#277d72" if chosen else "#5d7899"
        out.append(tx(85,y,candidate,17,color,weight=700 if chosen else 400))
        out.append(f'<rect x="333" y="{y-18}" width="580" height="27" rx="5" fill="#edf2f7"/>')
        out.append(f'<rect x="333" y="{y-18}" width="{580*(6-val)/5:.1f}" '
                   f'height="27" rx="5" fill="{color}" fill-opacity="0.88"/>')
        out.append(tx(930,y+3,f"{val:.3f}",18,weight=700 if chosen else 400))
        if chosen:
            out.append(tx(1020,y+3,"SELECTED",12,"#277d72",weight=700))
    out.append(tx(70,608,"Only these four development functions determined the frozen holdout DE setting.",13))
    out.append("</svg>")
    return "\n".join(out)+"\n"


def error_heatmap(rank_rows:list[dict])->str:
    lookup={(int(r["function_id"]),r["method"]):r for r in rank_rows}
    all_logs=[math.log10(float(r["relative_to_function_best"])) for r in rank_rows]
    denom=max(.4,float(np.quantile(all_logs,.93)))
    out=svg_header(1180,1420,"Fresh-seed heldout comparison | 25 functions",
                   "ABC / calibrated DE / jDE · 10 fresh paired seeds · 10k FE · relative 5e mean objective error")
    out.append('<rect x="52" y="113" width="1070" height="1250" rx="12" '
               'fill="white" stroke="#e5eaf2"/>')
    xs=[318,592,864]
    for j,m in enumerate(METHODS):
        out.append(tx(xs[j]+112,153,m.upper().replace("_","-"),17,COLORS[m],
                      anchor="middle",weight=700))
    for idx,fid in enumerate(TEST_FUNCTIONS):
        y=194+idx*44
        if idx%2==0:
            out.append(f'<rect x="68" y="{y-24}" width="1028" height="42" fill="#f7f9fc"/>')
        out.append(tx(91,y,f"F{fid}",17,weight=700))
        for j,method in enumerate(METHODS):
            ratio=float(lookup[(fid,method)]["relative_to_function_best"])
            frac=min(1.,math.log10(ratio)/denom)
            rgb=(int(227-100*frac),int(240-121*frac),int(247-101*frac))
            out.append(f'<rect x="{xs[j]}" y="{y-25}" width="232" height="35" '
                       f'rx="4" fill="rgb({rgb[0]},{rgb[1]},{rgb[2]})"/>')
            out.append(tx(xs[j]+116,y-2,f"{ratio:.2f}×",15,
                          anchor="middle",weight=700 if ratio==1 else 400))
    out.append(tx(75,1396,"Within each function: (1 + method mean error) / (1 + minimum method mean error); 1.00 is best.",13))
    out.append("</svg>")
    return "\n".join(out)+"\n"


def ranking_svg(stats:dict,tests:list[dict])->str:
    out=svg_header(1150,680,"Heldout-function ranks | ABC, tuned DE and jDE",
                   "25 calibration-excluded functions · 10 NEW seeds each · 750 true optimization runs")
    out.append('<rect x="56" y="112" width="1038" height="470" rx="14" '
               'fill="white" stroke="#e4eaf0"/>')
    out.append(tx(84,163,"Mean error ranks across 25 functions",19,weight=700))
    out.append(tx(711,163,"Mean-error winner count",19,weight=700))
    for i,m in enumerate(METHODS):
        y=228+i*102
        rank=stats["mean_function_ranks"][m]
        wins=stats["function_winner_counts"][m]
        out.append(tx(86,y,m.upper().replace("_","-"),18,COLORS[m],weight=700))
        out.append(f'<rect x="330" y="{y-17}" width="317" height="29" rx="5" fill="#e9edf3"/>')
        out.append(f'<rect x="330" y="{y-17}" width="{(3-rank)/2*317:.1f}" '
                   f'height="29" rx="5" fill="{COLORS[m]}"/>')
        out.append(tx(657,y+4,f"{rank:.3f}",16,weight=700))
        out.append(f'<rect x="813" y="{y-17}" width="165" height="29" rx="5" fill="#e9edf3"/>')
        out.append(f'<rect x="813" y="{y-17}" width="{165*wins/25:.1f}" '
                   f'height="29" rx="5" fill="{COLORS[m]}"/>')
        out.append(tx(987,y+5,f"{wins}/25",16,weight=700))
    out.append(tx(63,610,
                  f"Friedman Q={stats['friedman_statistic']:.3f}, permutation p={stats['permutation_p']:.4g} (20k samples); descriptive function-level tests",
                  14))
    out.append(tx(63,650,"Heldout only from current hyperparameter selection; all CEC functions appeared in prior BoundEvo research.",12))
    out.append("</svg>")
    return "\n".join(out)+"\n"


def convergence_svg(history:list[dict])->str:
    seen=defaultdict(dict)
    show=(1,12,17,25)
    for row in history:
        f=int(row["function_id"])
        if f in show:
            seen[(f,row["method"],int(row["repeat"]))][int(row["evaluations"])]=float(
                row["best_error"]
            )
    out=svg_header(1180,1010,"Actual convergence | Four preset heldout functions",
                   "Best-so-far log10(1+error) · n=10 · median + IQR bands · every 100 FE")
    for panel,fid in enumerate(show):
        left=86+(panel%2)*565
        top=171+(panel//2)*400
        width,height=421,274
        out.append(f'<rect x="{left-34}" y="{top-58}" width="{width+86}" '
                   f'height="{height+103}" rx="12" fill="white" stroke="#e3eaf1"/>')
        out.append(tx(left,top-25,f"F{fid} · 10 paired seeds",19,weight=700))
        ranges=[math.log10(1+v) for m in METHODS for i in range(10)
                for v in seen[(fid,m,i)].values()]
        ylo=max(0.,min(ranges)-.1); yhi=max(ranges)+.1
        def fx(fe:int,left=left,width=width)->float:
            return left+width*(fe-100)/9900
        def fy(val:float,top=top,height=height,yhi=yhi,ylo=ylo)->float:
            return top+height*(yhi-val)/(yhi-ylo)
        for step in range(5):
            val=ylo+(yhi-ylo)*step/4
            y=fy(val)
            out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+width}" '
                       f'y2="{y:.1f}" stroke="#e6edf4"/>')
            out.append(tx(left-9,y+4,f"{val:.1f}",12,anchor="end"))
        for fe in (100,2500,5000,7500,10000):
            out.append(tx(fx(fe),top+height+24,
                          str(fe) if fe==100 else f"{fe//1000}k",12,anchor="middle"))
        fes=tuple(range(100,10001,100))
        for method in METHODS:
            observations=[seen[(fid,method,i)] for i in range(10)]
            med=[];lower=[];upper=[]
            for fe in fes:
                vals=np.array([math.log10(1+d[fe]) for d in observations])
                lo,md,hi=np.quantile(vals,[.25,.5,.75])
                med.append(md);lower.append(lo);upper.append(hi)
            coords=[(fx(fe),fy(v)) for fe,v in zip(fes,upper)]
            coords += [(fx(fe),fy(v)) for fe,v in reversed(list(zip(fes,lower)))]
            pts=" ".join(f"{x:.1f},{y:.1f}" for x,y in coords)
            out.append(f'<polygon points="{pts}" fill="{COLORS[method]}" fill-opacity=".13"/>')
            path=" ".join(f"{'M' if j==0 else 'L'}{fx(fe):.1f},{fy(v):.1f}"
                          for j,(fe,v) in enumerate(zip(fes,med)))
            out.append(f'<path d="{path}" fill="none" stroke="{COLORS[method]}" stroke-width="2.9"/>')
    for i,m in enumerate(METHODS):
        x=165+i*315
        out.append(f'<line x1="{x}" y1="967" x2="{x+36}" y2="967" '
                   f'stroke="{COLORS[m]}" stroke-width="4"/>')
        out.append(tx(x+43,972,m.upper().replace("_","-"),14))
    out.append("</svg>")
    return "\n".join(out)+"\n"


def report(stats:dict,calib:dict,summary:list[dict],tests:list[dict])->str:
    means={(int(r["function_id"]),r["method"]):float(r["mean_error"]) for r in summary}
    lines=[
        "# Calibrated differential evolution and jDE: fresh-seed comparison",
        "",
        "**822 genuine original optimizer runs** in two explicitly separate "
        "cohorts: **72 calibration trials** on development CEC2017 "
        f"{list(DEV_FUNCTIONS)} (six conventional DE parameter candidates "
        "× 4 functions × 3 seeds), followed by **750 fresh-seed evaluation "
        "runs** on the remaining 25 retained CEC functions (ABC, one "
        "frozen calibrated DE, jDE × 25 functions × 10 seeds). "
        "Stored best-so-far records: **7,200 calibration checkpoints** "
        "and **75,000 evaluation checkpoints**. The evaluation seeds "
        "are never used for DE calibration.",
        "",
        "## Development-only winner",
        "",
        f"Selected **{calib['selected']}**: strategy {calib['strategy']}, "
        f"F={calib['mutation']}, CR={calib['crossover']}. "
        f"Average rank on four development functions = "
        f"**{calib['all_candidate_mean_ranks'][calib['selected']]:.4f}**. "
        "All six calibration candidates, objective values and source manifests "
        "are archived. Function choice is transparent, not a blind sample.",
        "",
        "## Evaluation-only function-block summary",
        "",
        "| Algorithm | Mean rank (lower better) | Lowest-mean-error functions | Hosted-runner mean seconds/run |",
        "|:---|---:|---:|---:|",
    ]
    for m in METHODS:
        lines.append(f"| {m} | {stats['mean_function_ranks'][m]:.4f} | "
                     f"{stats['function_winner_counts'][m]}/25 | "
                     f"{stats['mean_wall_seconds_per_run'][m]:.3f} |")
    lines.extend([
        "",
        f"Function-rank Friedman Q=**{stats['friedman_statistic']:.5f}**, "
        f"20,000-label permutation p=**{stats['permutation_p']:.7g}**. "
        "This is exploratory inference across curated and previously "
        "observed benchmark functions, not a distribution-free statement "
        "about all optimization problems.",
        "",
        "| Predeclared comparison | ABC function wins/losses/ties | Exact sign p | Holm p |",
        "|:---|---:|---:|---:|",
    ])
    for t in tests:
        lines.append(f"| {t['comparison']} | "
                     f"{t['abc_function_wins']}/{t['abc_function_losses']}/{t['ties']} | "
                     f"{t['exact_sign_p']:.7g} | {t['holm_sign_p']:.7g} |")
    lines.extend([
        "",
        "## Each of the 25 evaluation functions: 10-seed mean error",
        "",
        "| Function | ABC | Tuned DE | jDE |",
        "|:---|---:|---:|---:|",
    ])
    for fid in TEST_FUNCTIONS:
        values=[means[(fid,m)] for m in METHODS]
        minv=min(values)
        vals=[f"**{v:.6g}**" if v==minv else f"{v:.6g}" for v in values]
        lines.append(f"| F{fid} | "+" | ".join(vals)+" |")
    lines.extend([
        "",
        "## Methodological boundaries and negative results",
        "",
        "- Only four development functions and three seeds per DE candidate "
        "guide a six-configuration search; the selected DE may not be robust.",
        "- None of the 25 evaluation functions was used in **this round** of "
        "calibration, but all had already been studied in v0.13.0. "
        "Do not describe them as previously unseen functions.",
        "- jDE is a recognized classic self-adaptive baseline, not equivalent "
        "to SHADE, L-SHADE or optimally tuned current DE implementations.",
        "- Equal FE budgets do not imply equal wall time. Hosted runtime "
        "numbers are measured but not hardware-normalized.",
        "- Reference backend derives from published CEC2017 C functions; "
        "it is not the organizers' official C executable.",
        "- 10 seeds per function do not establish per-function significance; "
        "the fixed contrasts instead use function-level mean-error direction.",
        "",
        "[Development original data](calibration_trials.csv) · "
        "[Calibration original history](calibration_history.csv) · "
        "[All six candidate ranks](calibration_candidate_ranks.csv) · "
        "[Frozen winner/metadata](calibration_selection.json) · "
        "[750 new evaluation trials](evaluation_trials.csv) · "
        "[75,000 real checkpoints](evaluation_history.csv) · "
        "[Function/method bootstraps](summary.csv) · "
        "[25-function rank records](function_ranks.csv) · "
        "[Two Holm-adjusted paired tests](function_sign_tests.csv) · "
        "[Global summaries](global_statistics.json) · "
        "[Exact source manifests](environment.json) · "
        "[Pre-experiment protocol](../../calibrated_de_jde_protocol.md)",
        "",
    ])
    return "\n".join(lines)


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--calibration-dir",type=Path,required=True)
    parser.add_argument("--evaluation-dir",type=Path,required=True)
    parser.add_argument("--selection",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--figure-dir",type=Path,required=True)
    args=parser.parse_args()
    original,hist,selected,dev_scores,dev_board=verify(
        args.calibration_dir,args.evaluation_dir,args.selection
    )
    summary,ranks,tests,stats=analyze(original)
    out=args.output_dir
    out.mkdir(parents=True,exist_ok=True)
    calibration_trials=[]
    calibration_history=[]
    dev_manifests=[]
    for fid in DEV_FUNCTIONS:
        src=args.calibration_dir/f"f{fid}"
        calibration_trials.extend(csv_read(src/"trials.csv"))
        calibration_history.extend(csv_read(src/"history.csv"))
        dev_manifests.append(json.loads((src/"manifest.json").read_text(encoding="utf-8")))
    for name,rows in (
        ("calibration_trials.csv",calibration_trials),
        ("calibration_history.csv",calibration_history),
        ("calibration_candidate_ranks.csv",dev_board),
        ("calibration_candidate_function_scores.csv",dev_scores),
        ("evaluation_trials.csv",original),("evaluation_history.csv",hist),
        ("summary.csv",summary),("function_ranks.csv",ranks),
        ("function_sign_tests.csv",tests)
    ):
        csv_write(out/name,rows)
    (out/"calibration_selection.json").write_text(
        json.dumps(selected,indent=2)+"\n",encoding="utf-8"
    )
    (out/"global_statistics.json").write_text(
        json.dumps(stats,indent=2)+"\n",encoding="utf-8"
    )
    evaluation_manifests=[
        json.loads((args.evaluation_dir/f"shard{i}"/"manifest.json").read_text(encoding="utf-8"))
        for i in range(5)
    ]
    (out/"environment.json").write_text(
        json.dumps({
            "development_functions":list(DEV_FUNCTIONS),
            "evaluation_functions":list(TEST_FUNCTIONS),
            "methods":list(METHODS),
            "calibration_trials":72,"calibration_history":7200,
            "evaluation_trials":750,"evaluation_history":75000,
            "reference_commit":REFERENCE_COMMIT,
            "selected":selected["selected"],
            "calibration_source_commit":selected["calibration_source_commit"],
            "evaluation_source_commit":evaluation_manifests[0]["source_commit"],
            "calibration_data_sha256":selected["calibration_data_sha256"],
            "development_manifests":dev_manifests,
            "evaluation_manifests":evaluation_manifests,
            "python":sys.version,"numpy":np.__version__,
            "platform":platform.platform(),"analysis_utc":datetime.now(timezone.utc).isoformat(),
        },indent=2)+"\n",encoding="utf-8"
    )
    (out/"report.md").write_text(
        report(stats,selected,summary,tests),encoding="utf-8"
    )
    pictures={
        "cec2017-tuned-de-development-ranks.svg":calibration_svg(dev_board,selected),
        "cec2017-tuned-de-holdout-heatmap.svg":error_heatmap(ranks),
        "cec2017-tuned-de-holdout-ranks.svg":ranking_svg(stats,tests),
        "cec2017-tuned-de-holdout-convergence.svg":convergence_svg(hist),
    }
    args.figure_dir.mkdir(parents=True,exist_ok=True)
    for name,svg in pictures.items():
        ElementTree.fromstring(svg)
        (args.figure_dir/name).write_text(svg,encoding="utf-8")
    print("VERIFIED: 72 calibration and 750 heldout original optimizer trials; "
          "82,200 real convergence checkpoints; four scientific SVGs.")


if __name__=="__main__":
    main()
