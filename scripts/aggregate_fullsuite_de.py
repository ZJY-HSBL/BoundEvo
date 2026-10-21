"""Fail-closed aggregation, function-level inference and source-derived full-suite figures."""

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

from boundevo.cec2017 import PAPER_FUNCTION_IDS, REFERENCE_COMMIT

FUNCTIONS = tuple(PAPER_FUNCTION_IDS)
METHODS = ("abc", "abc_reverse", "de_rand1bin")
REPEATS = 5
BASE_SEED = 20261021
BUDGET = 10_000
CHECKPOINTS = 100
BOOTSTRAP = 10_000
PERMUTATIONS = 20_000
COLORS = {"abc": "#25618b", "abc_reverse": "#c17a39", "de_rand1bin": "#258c78"}
SIX_SHARDS = (
    (1, 3, 4, 5, 6), (7, 8, 9, 10, 11), (12, 13, 14, 15, 16),
    (17, 18, 19, 20, 21), (22, 23, 24, 25, 26), (27, 28, 29, 30),
)


def read(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError(f"missing actual original CEC2017 evidence: {path}")
    with path.open(newline="", encoding="utf-8") as stream:
        records = list(csv.DictReader(stream))
    if not records:
        raise ValueError(f"empty original experiment evidence: {path}")
    return records


def save(path: Path, records: list[dict]) -> None:
    if not records:
        raise ValueError("cannot publish an empty scientific record")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def exact_sign_test(wins: int, losses: int) -> float:
    n = wins + losses
    return min(1.0, 2 * sum(math.comb(n, j)
                           for j in range(min(wins, losses) + 1)) / 2**n)


def verify(source: Path) -> tuple[list[dict], list[dict], list[dict]]:
    originals, history, manifests = [], [], []
    original_sha = None
    for shard_id, fids in enumerate(SIX_SHARDS):
        folder = source/f"shard{shard_id}"
        manifest = json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
        expected = {
            "shard_id": shard_id, "functions": list(fids),
            "official_function_ids": list(FUNCTIONS), "methods": list(METHODS),
            "dimension": 30, "repeats": REPEATS, "base_seed": BASE_SEED,
            "evaluations": BUDGET, "history_interval": 100,
            "de_population": 100, "de_mutation": 0.8, "de_crossover": 0.9,
            "reference_commit": REFERENCE_COMMIT,
        }
        if any(manifest.get(k) != v for k, v in expected.items()):
            raise ValueError(f"incorrect frozen experiment settings in shard{shard_id}")
        if not manifest.get("source_commit") or (
            original_sha is not None and original_sha != manifest["source_commit"]
        ):
            raise ValueError(f"provenance mismatch in shard{shard_id}")
        original_sha = manifest["source_commit"]
        batch = read(folder/"trials.csv")
        if len(batch) != len(fids)*REPEATS*len(METHODS):
            raise ValueError(f"incomplete experimental shard{shard_id}")
        originals.extend(batch)
        history.extend(read(folder/"history.csv"))
        manifests.append(manifest)
    expected_keys = {(fid, rep, method) for fid in FUNCTIONS
                     for rep in range(REPEATS) for method in METHODS}
    observed = {}
    for row in originals:
        key = (int(row["function_id"]), int(row["repeat"]), row["method"])
        if key not in expected_keys or key in observed:
            raise ValueError(f"duplicated or unexpected CEC2017 trial {key}")
        fid, rep, method = key
        if (int(row["seed"]) != BASE_SEED + 10_000*fid + rep
                or int(row["dimension"]) != 30
                or int(row["evaluations"]) != BUDGET
                or int(row["coefficient_attempts"]) != (0 if method == "de_rand1bin"
                                                       else BUDGET-100)):
            raise ValueError(f"unequal evaluation budget or wrong method/seed {key}")
        if any(not math.isfinite(float(row[k])) for k in
               ("objective", "optimum", "error", "elapsed_seconds", "violation")):
            raise ValueError(f"nonfinite original optimization result {key}")
        objective, opt, error = (float(row[k]) for k in ("objective","optimum","error"))
        if (opt != fid*100.0 or error < 0
                or not math.isclose(objective-opt, error, rel_tol=1e-10, abs_tol=1e-6)):
            raise ValueError(f"invalid official CEC optimum or actual objective error {key}")
        observed[key] = row
    if len(originals) != 435 or set(observed) != expected_keys:
        raise ValueError("full CEC2017 replication requires exactly 435 original trials")
    traces = defaultdict(list)
    for h in history:
        key = (int(h["function_id"]), int(h["repeat"]), h["method"])
        if key not in expected_keys:
            raise ValueError(f"unrecognized original convergence trajectory {key}")
        if (int(h["seed"]) != int(observed[key]["seed"])
                or int(h["dimension"]) != 30
                or not math.isfinite(float(h["best_error"]))):
            raise ValueError(f"corrupt scientific checkpoint {key}")
        traces[key].append(h)
    if len(history) != 43_500 or set(traces) != expected_keys:
        raise ValueError("missing original 43,500 recorded objective checkpoints")
    actual_grid = list(range(100, 10_001, 100))
    for key, trace in traces.items():
        trace.sort(key=lambda x: int(x["evaluations"]))
        fes = [int(s["evaluations"]) for s in trace]
        errors = [float(s["best_error"]) for s in trace]
        if (fes != actual_grid or any(v < 0 for v in errors)
                or any(next_err > prev + 1e-7 for prev, next_err in pairwise(errors))
                or not math.isclose(
                    errors[-1], float(observed[key]["error"]),
                    rel_tol=1e-10, abs_tol=1e-6
                )):
            raise ValueError(f"incomplete or invalid actual best-so-far curve {key}")
    for fid in FUNCTIONS:
        for rep in range(REPEATS):
            start_errors = [float(traces[(fid,rep,m)][0]["best_error"]) for m in METHODS]
            if max(start_errors)-min(start_errors) > 1e-7:
                raise ValueError(f"paired methods did not share identical start F{fid} seed{rep}")
    originals.sort(key=lambda r: (int(r["function_id"]), int(r["repeat"]), r["method"]))
    history.sort(key=lambda h: (
        int(h["function_id"]), int(h["repeat"]), h["method"], int(h["evaluations"])
    ))
    return originals, history, manifests


def rank3(values: list[float]) -> list[float]:
    if len(values) != 3 or any(not math.isfinite(v) for v in values):
        raise ValueError("three finite method means are required for function ranks")
    return [1.0 + sum(v < value for v in values)
            + 0.5*(sum(v == value for v in values)-1)
            for value in values]


def friedman_statistic(rank_matrix: np.ndarray) -> float:
    if rank_matrix.ndim != 2 or rank_matrix.shape[1] != 3:
        raise ValueError("requires n-by-3 function ranks")
    n, k = rank_matrix.shape
    means = rank_matrix.mean(axis=0)
    return float(12*n/(k*(k+1))*np.sum((means-(k+1)/2)**2))


def analyze(trials: list[dict]) -> tuple[list[dict], list[dict], list[dict], dict]:
    index = {(int(t["function_id"]), int(t["repeat"]), t["method"]): t for t in trials}
    if len(index) != 435:
        raise ValueError("statistics require 435 complete real optimizer outcomes")
    summaries: list[dict] = []
    ranks: list[dict] = []
    for fid in FUNCTIONS:
        rng = np.random.default_rng(BASE_SEED + fid + 1)
        samples = rng.integers(0, REPEATS, size=(BOOTSTRAP,REPEATS))
        means = []
        for method in METHODS:
            vals = np.asarray([float(index[(fid,rep,method)]["error"])
                               for rep in range(REPEATS)],dtype=np.float64)
            ci = np.quantile(vals[samples].mean(axis=1),[0.025,0.975])
            mean=float(vals.mean())
            means.append(mean)
            summaries.append({
                "function_id":fid, "method":method, "seeds":REPEATS,
                "mean_error":mean, "median_error":float(np.median(vals)),
                "std_error":float(np.std(vals,ddof=1)),
                "bootstrap_mean_ci95_low":float(ci[0]),
                "bootstrap_mean_ci95_high":float(ci[1]),
                "mean_elapsed_seconds":float(np.mean([
                    float(index[(fid,rep,method)]["elapsed_seconds"])
                    for rep in range(REPEATS)
                ])),
            })
        for m, value, rank in zip(METHODS,means,rank3(means)):
            ranks.append({
                "function_id":fid, "method":m, "mean_error":value,
                "rank":rank, "relative_to_function_best":(
                    (1.0+value)/(1.0+min(means))
                ),
            })

    r_matrix = np.asarray([
        [next(float(t["rank"]) for t in ranks
              if int(t["function_id"])==fid and t["method"]==m)
         for m in METHODS]
        for fid in FUNCTIONS],dtype=float
    )
    observed = friedman_statistic(r_matrix)
    prng = np.random.default_rng(20261023)
    count = 0
    for _ in range(PERMUTATIONS):
        permuted = np.stack([row[prng.permutation(3)] for row in r_matrix])
        if friedman_statistic(permuted) >= observed-1e-12:
            count += 1
    global_p=(1+count)/(PERMUTATIONS+1)
    cross_tests=[]
    for a,b in (("abc","de_rand1bin"),("abc","abc_reverse"),
                ("abc_reverse","de_rand1bin")):
        wins=sum(
            next(float(r["mean_error"]) for r in ranks
                 if int(r["function_id"])==fid and r["method"]==a)
            <
            next(float(r["mean_error"]) for r in ranks
                 if int(r["function_id"])==fid and r["method"]==b)
            for fid in FUNCTIONS
        )
        losses=sum(
            next(float(r["mean_error"]) for r in ranks
                 if int(r["function_id"])==fid and r["method"]==a)
            >
            next(float(r["mean_error"]) for r in ranks
                 if int(r["function_id"])==fid and r["method"]==b)
            for fid in FUNCTIONS
        )
        cross_tests.append({
            "method_a":a,"method_b":b,"a_function_wins":wins,
            "a_function_losses":losses,
            "ties":29-wins-losses,
            "exact_function_sign_p":exact_sign_test(wins,losses),
            "holm_function_sign_p":1.0,
        })
    correction=0.0
    for i, idx in enumerate(sorted(range(3),key=lambda i: cross_tests[i]["exact_function_sign_p"])):
        correction=max(correction,min(1.0,cross_tests[idx]["exact_function_sign_p"]*(3-i)))
        cross_tests[idx]["holm_function_sign_p"]=correction
    global_stats={
        "functions":29,"algorithms":list(METHODS),"seeds_per_function":REPEATS,
        "trials":435, "history_rows":43500,
        "function_block_mean_ranks":{
            method:float(r_matrix[:,i].mean()) for i,method in enumerate(METHODS)
        },
        "function_best_mean_error_counts":{
            method:int(sum(row[i]==min(row) for row in r_matrix))
            for i,method in enumerate(METHODS)
        },
        "friedman_rank_statistic":observed,
        "permutation_iterations":PERMUTATIONS,
        "permutation_exceedances":count,
        "permutation_p":global_p,
        "bootstrap_resamples":BOOTSTRAP,
        "note":"Exploratory function-block label permutation, not an unbiased sample of all tasks",
    }
    return summaries,ranks,cross_tests,global_stats


def svg_intro(width:int,height:int,title:str,subtitle:str)->list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
        f'<rect width="{width}" height="{height}" fill="#f8fafc"/>',
        f'<text x="56" y="58" font-size="27" font-weight="700" '
        f'font-family="Arial,sans-serif" fill="#19314a">{escape(title)}</text>',
        f'<text x="56" y="89" font-size="15" font-family="Arial,sans-serif" '
        f'fill="#586c80">{escape(subtitle)}</text>',
    ]


def label(x:float,y:float,value:str,size:int=14,color:str="#334155",
          anchor:str="start",weight:int=400)->str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
        f'font-family="Arial,sans-serif" text-anchor="{anchor}" '
        f'font-weight="{weight}" fill="{color}">{escape(value)}</text>'
    )


def heatmap_svg(ranks:list[dict])->str:
    rows={(int(r["function_id"]),r["method"]):r for r in ranks}
    data=[math.log10(float(r["relative_to_function_best"])) for r in ranks]
    cap=max(1.,float(np.quantile(data,0.93)))
    out=svg_intro(1150,1550,"Full CEC2017 | Relative mean-error heatmap",
                  "29/29 retained functions · 30D · five NEW paired seeds · 10k FE · 435 true optimizer runs")
    out.append('<rect x="56" y="115" width="1038" height="1357" rx="13" '
               'fill="#ffffff" stroke="#dfe8ef"/>')
    xcols=(330,580,830)
    for i,m in enumerate(METHODS):
        out.append(label(xcols[i]+105,158,m.upper().replace("_","-"),18,
                         COLORS[m],"middle",700))
    out.append(label(86,158,"CEC2017",17,weight=700))
    for i,fid in enumerate(FUNCTIONS):
        y=194+i*42
        if i%2==0:
            out.append(f'<rect x="72" y="{y-24}" width="996" height="42" '
                       'fill="#f7f9fc"/>')
        out.append(label(104,y+2,f"F{fid}",16,weight=700))
        for j,m in enumerate(METHODS):
            ratio=float(rows[(fid,m)]["relative_to_function_best"])
            z=math.log10(ratio)
            frac=min(1.,z/cap)
            # Accent background intensity is driven only by actual error ratio.
            red=int(228-103*frac)
            green=int(242-126*frac)
            blue=int(248-101*frac)
            out.append(f'<rect x="{xcols[j]}" y="{y-24}" width="212" height="34" '
                       f'rx="5" fill="rgb({red},{green},{blue})"/>')
            out.append(label(xcols[j]+106,y-2,f"{ratio:,.2f}×",15,
                             "#21354c","middle",700 if ratio==1 else 400))
    out.append(label(74,1518,"Cell = (1 + method mean error) / (1 + best method mean error) within each function. Lower = better.",13))
    out.append("</svg>")
    return "\n".join(out)+"\n"


def ranks_svg(stats:dict,tests:list[dict])->str:
    out=svg_intro(1130,650,"Across 29 functions | Algorithm ranks and wins",
                  "Function-block evaluation · fixed 10k FE · rank 1 = smallest mean error · exploratory")
    x0=72
    out.append('<rect x="56" y="117" width="1010" height="437" rx="16" '
               'fill="#ffffff" stroke="#dfe8ef"/>')
    out.append(label(94,162,"Average rank, 29 function blocks",19,weight=700))
    out.append(label(665,162,"Best mean error on N functions",19,weight=700))
    ranks=stats["function_block_mean_ranks"]
    wins=stats["function_best_mean_error_counts"]
    for i,m in enumerate(METHODS):
        y=224+i*101
        out.append(label(95,y+13,m.upper().replace("_","-"),15,COLORS[m],weight=700))
        out.append(f'<rect x="260" y="{y-6}" width="300" height="28" rx="5" fill="#e9eff5"/>')
        out.append(f'<rect x="260" y="{y-6}" width="{(3-ranks[m])/2*300:.2f}" '
                   f'height="28" rx="5" fill="{COLORS[m]}" opacity="0.88"/>')
        out.append(label(570,y+15,f"{ranks[m]:.3f}",16,weight=700))
        out.append(f'<rect x="780" y="{y-6}" width="190" height="28" rx="5" fill="#edf2f7"/>')
        out.append(f'<rect x="780" y="{y-6}" width="{wins[m]/29*190:.2f}" '
                   f'height="28" rx="5" fill="{COLORS[m]}" opacity="0.88"/>')
        out.append(label(984,y+16,f"{wins[m]}/29",16,weight=700))
    out.append(label(x0,590,f"Function-label permutation Friedman Q = {stats['friedman_rank_statistic']:.4f}; "
                     f"Monte Carlo p = {stats['permutation_p']:.5g} ({PERMUTATIONS:,} permutations)",15))
    out.append(label(x0,625,"Function-level rank inference is exploratory; five paired seeds per function and benchmark selection limit generalization.",13))
    out.append("</svg>")
    return "\n".join(out)+"\n"


def trajectory_svg(history:list[dict])->str:
    fids=(3,10,20,30)
    lookup=defaultdict(list)
    for row in history:
        fid=int(row["function_id"])
        if fid in fids:
            lookup[(fid,row["method"],int(row["repeat"]))].append(
                (int(row["evaluations"]),float(row["best_error"]))
            )
    out=svg_intro(1200,1020,"Convergence | 4 prespecified representative functions",
                  "Actual best-so-far error · median and seed IQR · five matched seeds · 10k FE · log10(1 + error)")
    for i,fid in enumerate(fids):
        x0=95+(i%2)*570
        y0=175+(i//2)*415
        width,height=415,287
        out.append(f'<rect x="{x0-35}" y="{y0-60}" width="{width+86}" height="{height+101}" '
                   'rx="14" fill="#ffffff" stroke="#e1e8ef"/>')
        out.append(label(x0,y0-28,f"F{fid} | 5 matched seeds",20,weight=700))
        allvals=[math.log10(1+v) for m in METHODS for rep in range(REPEATS)
                 for fe,v in lookup[(fid,m,rep)]]
        ymin=max(0.,min(allvals)-0.15)
        ymax=max(allvals)+0.15
        fx=lambda fe, x0=x0, width=width: x0+width*(fe-100)/9900
        fy=lambda z, y0=y0, height=height, ymax=ymax, ymin=ymin: y0+height*(ymax-z)/(ymax-ymin)
        for tick in range(5):
            value=ymin+(ymax-ymin)*tick/4
            y=fy(value)
            out.append(f'<line x1="{x0}" y1="{y:.2f}" x2="{x0+width}" y2="{y:.2f}" stroke="#e5edf4"/>')
            out.append(label(x0-11,y+4,f"{value:.1f}",12,"#64748b","end"))
        for fe in (100,2500,5000,7500,10000):
            xx=fx(fe)
            out.append(label(xx,y0+height+24,f"{fe//1000}k" if fe>100 else "100",12,
                             "#64748b","middle"))
        for m in METHODS:
            series=[dict(lookup[(fid,m,rep)]) for rep in range(REPEATS)]
            grid=list(range(100,10_001,100))
            med=[float(np.median([math.log10(1+s[fe]) for s in series]))
                 for fe in grid]
            lo=[float(np.quantile([math.log10(1+s[fe]) for s in series],0.25))
                for fe in grid]
            hi=[float(np.quantile([math.log10(1+s[fe]) for s in series],0.75))
                for fe in grid]
            ribbon=[(fx(fe),fy(val)) for fe,val in zip(grid,hi)]
            ribbon += [(fx(fe),fy(val)) for fe,val in
                       reversed(list(zip(grid,lo)))]
            outline=" ".join(f"{x:.1f},{y:.1f}" for x,y in ribbon)
            out.append(f'<polygon points="{outline}" fill="{COLORS[m]}" fill-opacity="0.14"/>')
            pts=" ".join(f"{'M' if i==0 else 'L'}{fx(fe):.1f},{fy(val):.1f}"
                         for i,(fe,val) in enumerate(zip(grid,med)))
            out.append(f'<path d="{pts}" fill="none" stroke="{COLORS[m]}" stroke-width="2.8"/>')
    for j,m in enumerate(METHODS):
        x=190+285*j
        out.append(f'<line x1="{x}" y1="970" x2="{x+35}" y2="970" stroke="{COLORS[m]}" stroke-width="4"/>')
        out.append(label(x+44,975,m.upper().replace("_","-"),14))
    out.append("</svg>")
    return "\n".join(out)+"\n"


def report(stats:dict,summary:list[dict],ranks:list[dict],cross:list[dict])->str:
    index={(int(r["function_id"]),r["method"]):r for r in summary}
    leaderboard=stats["function_block_mean_ranks"]
    lines=[
        "# Full 29-function CEC2017 comparison with generational DE/rand/1/bin",
        "",
        "**435 original optimization trials**, F1/F3–F30, D=30, 10k FE, "
        "five matched new seeds per function, ABC / ABC-Reverse / DE/rand/1/bin. "
        "**43,500 real convergence checkpoint rows**; common sampled initial "
        "population for each function and seed. New benchmark control used "
        "F=0.8, CR=0.9, NP=100, forced binomial donor coordinate, generational "
        "greedy one-to-one replacement and box projection. These are one fixed "
        "baseline configuration, not an exhaustive DE hyperparameter search.",
        "",
        "## Global function-block result",
        "",
        "| Method | Average function rank (smaller better) | Functions with smallest mean error |",
        "|:---|---:|---:|",
    ]
    for m in METHODS:
        lines.append(f"| {m} | {leaderboard[m]:.4f} | "
                     f"{stats['function_best_mean_error_counts'][m]}/29 |")
    lines.extend([
        "",
        f"Friedman function-rank statistic = **{stats['friedman_rank_statistic']:.6g}**; "
        f"random-label block permutation p = **{stats['permutation_p']:.6g}**, "
        f"{PERMUTATIONS:,} fixed-RNG resamples. This inference assumes function-block "
        "algorithm-label exchangeability under the null, and only covers the "
        "CEC2017 function collection. It is not evidence for all optimizers/problems.",
        "",
        "### Across-function pairwise directions (Holm-adjusted across three tests)",
        "",
        "| Comparator | A wins / B wins / ties (29 functions) | Exact sign p | Holm p |",
        "|:---|---:|---:|---:|",
    ])
    for r in cross:
        lines.append(f"| {r['method_a']} vs {r['method_b']} | "
                     f"{r['a_function_wins']}/{r['a_function_losses']}/{r['ties']} | "
                     f"{r['exact_function_sign_p']:.6g} | {r['holm_function_sign_p']:.6g} |")
    lines.extend([
        "",
        "These tests compare **within-function five-seed means** and account for "
        "function scales by using direction of advantage, not raw average error. "
        "They do **not** test each individual function at five-seed resolution.",
        "",
        "## All 29 empirical function means",
        "",
        "| Function | ABC | ABC-Reverse | DE/rand/1/bin |",
        "|:---|---:|---:|---:|",
    ])
    for fid in FUNCTIONS:
        means=[float(index[(fid,m)]["mean_error"]) for m in METHODS]
        best=min(means)
        fmt=[f"**{v:.6g}**" if v==best else f"{v:.6g}" for v in means]
        lines.append(f"| F{fid} | "+" | ".join(fmt)+" |")
    lines.extend([
        "",
        "### Scientific evidence and interpretation boundaries",
        "",
        "- Exactly 29 retained official CEC2017 function IDs, excluding the withdrawn F2.",
        "- Backend: pinned independent C-derived Python reference, *not* CEC organizers' original C.",
        "- All 435 runs reached FE=10,000 with exactly 100 unique checkpoints; "
        "every endpoint and initial paired value was cross-validated.",
        "- All 435 optimizer runs are new, **not** the previously published "
        "144-run or 200-run mechanism and limited-function cohorts.",
        "- All reported significance is exploratory; curated functions are "
        "not a random sample of general optimization tasks. Five seeds per "
        "function and fixed DE hyperparameters leave considerable uncertainty.",
        "- Equal function evaluations do not imply equal iteration count or "
        "equal wall-clock cost. The DE baseline has no local polishing.",
        "",
        "[435 original trials](trials.csv) · [43,500 checkpoints](history.csv) · "
        "[87 function-method bootstrap summaries](summary.csv) · "
        "[87 function ranks](function_ranks.csv) · "
        "[three corrected function-sign tests](function_sign_tests.csv) · "
        "[global rank and permutation statistics](global_statistics.json) · "
        "[exact environment and shard provenance](environment.json) · "
        "[frozen protocol](../../fullsuite_de_protocol.md)",
        "",
    ])
    return "\n".join(lines)


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--figure-dir",type=Path,required=True)
    args=p.parse_args()
    original,history,sources=verify(args.input_dir)
    summary,ranks,cross,stats=analyze(original)
    out=args.output_dir
    for name,records in (
        ("trials.csv",original),("history.csv",history),("summary.csv",summary),
        ("function_ranks.csv",ranks),("function_sign_tests.csv",cross)
    ):
        save(out/name,records)
    (out/"global_statistics.json").write_text(json.dumps(stats,indent=2)+"\n",encoding="utf-8")
    (out/"environment.json").write_text(json.dumps({
        "functions":list(FUNCTIONS),"methods":list(METHODS),"dimension":30,
        "repeats":REPEATS,"evaluations":BUDGET,"base_seed":BASE_SEED,
        "trials":len(original),"history_rows":len(history),
        "reference_commit":REFERENCE_COMMIT,"source_manifests":sources,
        "bootstrap_samples":BOOTSTRAP,"permutation_samples":PERMUTATIONS,
        "analysis_python":sys.version,"numpy":np.__version__,
        "platform":platform.platform(),
        "generated_utc":datetime.now(timezone.utc).isoformat(),
    },indent=2)+"\n",encoding="utf-8")
    (out/"report.md").write_text(report(stats,summary,ranks,cross),encoding="utf-8")
    args.figure_dir.mkdir(parents=True,exist_ok=True)
    imgs={
        "cec2017-fullsuite-de-relative-heatmap.svg":heatmap_svg(ranks),
        "cec2017-fullsuite-de-ranks.svg":ranks_svg(stats,cross),
        "cec2017-fullsuite-de-four-convergence.svg":trajectory_svg(history),
    }
    for name,svg in imgs.items():
        ElementTree.fromstring(svg)
        (args.figure_dir/name).write_text(svg,encoding="utf-8")
    print(f"Validated {len(original)} genuine full-CEC optimization runs, "
          f"{len(history)} original FE checkpoints; generated three empirical plots.")


if __name__=="__main__":
    main()
